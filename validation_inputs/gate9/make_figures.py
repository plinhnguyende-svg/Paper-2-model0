from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
p=pd.read_csv(P/'policy_simulation_summary.csv')
fig,ax=plt.subplots(figsize=(8,5))
ax.scatter(p['volume_mean'],p['HHI_mean'],s=110)
for _,r in p.iterrows(): ax.annotate(r['rule'],(r['volume_mean'],r['HHI_mean']),xytext=(7,6),textcoords='offset points')
ax.set_xlabel('Mean executed volume, hypothetical TCO2 per 650 arrivals')
ax.set_ylabel('Mean final project-inventory HHI')
ax.set_title('Fee-policy trade-off in a synthetic biochar pool')
ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(P/'figure_policy_tradeoffs.png',dpi=170);plt.close(fig)

q=pd.read_csv(P/'maxfee_execution_stress_summary.csv')
fig,ax=plt.subplots(figsize=(9,5))
ax.bar(q['policy'],100*q['success_rate_given_submit'])
ax.set_ylim(0,105);ax.set_ylabel('Completed transactions among submitted (%)')
ax.set_title('Synthetic execution stress: maxFee cap design')
ax.tick_params(axis='x',rotation=20);fig.tight_layout();fig.savefig(P/'figure_execution_caps.png',dpi=170);plt.close(fig)

b=pd.read_csv(P/'boundary_experiment.csv')
fig,ax=plt.subplots(figsize=(8,5))
ax.plot(b.other_project_inventory,b.redeem_fee_char,marker='o',label='Redeem 10 TCO2 from dominant project')
ax.plot(b.other_project_inventory,b.dominant_deposit_fee_char,marker='s',label='Deposit 10 TCO2 to dominant project')
ax.set_xscale('symlog',linthresh=.001);ax.set_xlabel('Other project inventory epsilon (TCO2)')
ax.set_ylabel('Fee in CHAR')
ax.set_title('Single-project boundary: source-formula discontinuity')
ax.legend();ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(P/'figure_boundary.png',dpi=170);plt.close(fig)
