#!/usr/bin/env python3
"""Run recovered, unchanged Gates 9-13 in temporary copies, compare saved summaries."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='results/gate18/replay_ci')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    references=root/'results/gate18/original_replay'
    reference_map=json.loads((root/'config/replay_reference_map.json').read_text())
    runs=[(9,['-m','unittest','test_gate9','-v']), (9,['gate9_model.py']),
          (10,['gate10_mechanism.py']), (11,['gate11_design.py','--reps','40','--rounds','150']),
          (11,['post_analysis.py']), (12,['gate12_microfoundation.py']),
          (13,['partial_identification.py'])]
    comparisons=[]
    with tempfile.TemporaryDirectory(prefix='gate18_originals_') as temp:
        work=Path(temp)
        for gate in range(9,14):
            shutil.copytree(root/'validation_inputs'/f'gate{gate}',work/f'gate{gate}')
            external=root/'data/external/gate18'/f'gate{gate}'
            if external.exists():
                shutil.copytree(external,work/f'gate{gate}',dirs_exist_ok=True)
        for i,(gate,command) in enumerate(runs):
            result=subprocess.run([sys.executable,*command],cwd=work/f'gate{gate}',
                                  capture_output=True,text=True,timeout=240)
            (out/f'{i}_gate{gate}.log').write_text(result.stdout+'\n'+result.stderr)
            if result.returncode:
                raise RuntimeError(f'Gate {gate} replay failed; see archived log')
            print(f'Gate {gate}: command {i} passed',flush=True)
        for gatefolder in sorted(references.iterdir()):
            gate=int(gatefolder.name.removeprefix('gate'))
            for reference in gatefolder.glob('*.csv'):
                original_name=reference_map[str(reference.relative_to(references))]
                candidates=list((work/f'gate{gate}').rglob(original_name))
                if len(candidates)!=1:
                    raise RuntimeError(f'Unresolved output {gatefolder.name}/{reference.name}')
                a=pd.read_csv(reference);b=pd.read_csv(candidates[0])
                ok=list(a.columns)==list(b.columns) and a.shape==b.shape
                if ok:
                    for column in a:
                        if pd.api.types.is_numeric_dtype(a[column]) and pd.api.types.is_numeric_dtype(b[column]):
                            ok=bool(ok and np.allclose(a[column],b[column],rtol=1e-10,atol=1e-10,equal_nan=True))
                        else:
                            ok=bool(ok and a[column].fillna('').equals(b[column].fillna('')))
                comparisons.append(dict(gate=gate,file=reference.name,rows=len(b),match=ok))
        full=pd.read_csv(work/'gate11/data/replications_SYNTHETIC.csv')
        assert len(full)==6720
        assert all(x['match'] for x in comparisons)
    report=dict(status='ORIGINAL_NUMERICAL_REPLAY_PASS',saved_summary_comparisons=comparisons,
                gate11_simulation_replications=6720,
                scope='CI compares saved small summaries; local archive-to-replay audit additionally checked 27 regenerated CSVs including large panels. No empirical inference.')
    (out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: {len(comparisons)} saved summaries match; Gate 11 has 6720 simulation replications')


if __name__=='__main__':
    main()
