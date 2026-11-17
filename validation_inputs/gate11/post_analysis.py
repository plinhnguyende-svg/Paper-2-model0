#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent; D=R/'data';F=R/'figures';F.mkdir(exist_ok=True)
raw=pd.read_csv(D/'replications_SYNTHETIC.csv')
means=pd.read_csv(D/'policy_scenario_means_SYNTHETIC.csv')
sel=pd.read_csv(D/'selected_holdout_SYNTHETIC.csv')
policy=str(sel.selected_policy.iloc[0]);buffer=float(sel.cap_buffer.iloc[0]);
# paired by identical scenario and random seed, only holdout replications
rows=[]
for scenario in sorted(raw.scenario.unique()):
    base=raw[(raw.group=='holdout')&(raw.scenario==scenario)&(raw.policy=='legacy')&(raw.cap_buffer==.15)].set_index('rep')
    pp=raw[(raw.group=='holdout')&(raw.scenario==scenario)&(raw.policy==policy)&(raw.cap_buffer==buffer)].set_index('rep')
    for field in ['volume','gains','hhi','completion','fees','completed']:
        diff=(pp[field]-base[field]).dropna();n=len(diff);sd=diff.std(ddof=1);sem=sd/np.sqrt(n);cr=student_t.ppf(.975,n-1)
        rows.append(dict(scenario=scenario,metric=field,n_holdout=n,mean_difference=diff.mean(),
            lower_95=diff.mean()-cr*sem,upper_95=diff.mean()+cr*sem))
ci=pd.DataFrame(rows);ci.to_csv(D/'paired_holdout_differences_CI_SYNTHETIC.csv',index=False)
# Explicit revenue shares are illustrative generic recipients, never 'producers' in this dataset.
shares=[.3,.5,.7,1.0]
types=[]
for row in means[(means.group=='holdout') & (means.policy==policy)&(means.cap_buffer==buffer)].itertuples(index=False):
    for a in shares:
        types.append(dict(scenario=row.scenario,share_A_assumed=a,share_B_assumed=1-a,
            received_A_CHAR=row.fees*a,received_B_CHAR=row.fees*(1-a),
            fee_distribution_HHI=a*a+(1-a)*(1-a),total_fees_CHAR=row.fees,
            producer_attribution='UNVERIFIED'))
pd.DataFrame(types).to_csv(D/'hypothetical_fee_recipient_splits_SYNTHETIC.csv',index=False)
# Trade-off pairs, all holdout policy/buffer scenarios, average normalized by legacy per scenario
base=means[(means.group=='holdout')&(means.policy=='legacy')&(means.cap_buffer==.15)].set_index('scenario')
rows=[]
for (p,b),group in means[means.group=='holdout'].groupby(['policy','cap_buffer']):
    ratios=[];dH=[];dC=[]
    for row in group.itertuples(index=False):
        ref=base.loc[row.scenario]
        ratios.append(row.volume/ref.volume);dH.append(row.hhi-ref.hhi);dC.append(row.completion-ref.completion)
    rows.append(dict(policy=p,buffer=b,worst_case_volume_ratio=min(ratios),
        max_HHI_increase=max(dH),worst_completion_drop=min(dC)))
pd.DataFrame(rows).to_csv(D/'holdout_policy_tradeoffs_SYNTHETIC.csv',index=False)
# Source & policy fee curves; only real-number formulas.
import sys
sys.path.insert(0,str(R))
from gate11_design import policy_fee
q=np.linspace(10,100,250);Q=100.;x=10.
fig,ax=plt.subplots(figsize=(9,5))
for p in ['legacy','smooth_0.01','clip_0.10','extension_0.001']:
    y=[policy_fee('D',float(v),Q,x,p) for v in q]
    ax.plot(q/Q*100,y,label=p)
ax.set_xlabel('Project share before deposit (%)'); ax.set_ylabel('Deposit fee on 10 TCO2 (CHAR)')
ax.set_title('Smart-contract fee design: continuity versus incentives (real-number model)'); ax.legend();fig.tight_layout()
fig.savefig(F/'fee_design_monotonicity.png',dpi=165);plt.close(fig)
# paired scenario comparison
fig,ax=plt.subplots(figsize=(9,5))
chosen=means[(means.group=='holdout')&(means.policy==policy)&(means.cap_buffer==buffer)].set_index('scenario')
labels=['7-project snapshot','Near-monopoly (synthetic)','Single-project (synthetic)']
scenarios=['published_7project_snapshot','near_monopoly_SYNTHETIC','exact_single_project_SYNTHETIC']
x0=np.arange(len(scenarios)); width=.35
ax.bar(x0-width/2,[base.loc[s].volume for s in scenarios],width,label='Legacy with 0.15 cap buffer')
ax.bar(x0+width/2,[chosen.loc[s].volume for s in scenarios],width,label=f'{policy} with {buffer} cap buffer')
ax.set_xticks(x0,labels);ax.set_ylabel('Executed eligible TCO2 per simulation replication')
ax.set_title('Holdout results: simulated throughput, not observed CHAR activity')
ax.legend(fontsize=9);fig.tight_layout();fig.savefig(F/'holdout_throughput.png',dpi=165);plt.close(fig)
print('saved',len(ci),'paired CI rows')
print(ci.query("metric in ['volume','hhi']").to_string(index=False))
