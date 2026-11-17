"""Independent Decimal(60 digits) spot-check of REAL-NUMBER source fee.
Not EVM/PRBMath equivalence. High precision reference quantifies float cancellation.
"""
from decimal import Decimal, localcontext
import csv
from pathlib import Path
OUT=Path(__file__).resolve().parent/'data'/'high_precision_fee_checks.csv'

def d(x): return Decimal(str(x))

def fees(e):
    q=d(100); Q=q+e; x=d(10); a=q/Q;b=(q+x)/(Q+x)
    ln10=d(10).ln()
    D=d('.18')*(q*((d(1)-d('.99')*a).ln()/ln10)-(q+x)*((d(1)-d('.99')*b).ln()/ln10))
    ra=q/Q;rb=(q-x)/(Q-x)
    R=d('.3')*((q-x)*((rb+d('.1')).ln()/ln10)-q*((ra+d('.1')).ln()/ln10)+x*((d('1.1')).ln()/ln10))
    return D,R

if __name__=='__main__':
    with localcontext() as ctx:
      ctx.prec=65
      with open(OUT,'w',newline='') as f:
       w=csv.writer(f);w.writerow(['second_project_tco2','deposit_decimal_high_precision','redeem_decimal_high_precision','redeem_float_gate10','float_minus_decimal','status'])
       from gate10_mechanism import source_fee
       for e in ['1','0.1','0.01','0.001','0.00001','0.0000001','0.000000001']:
        D,R=fees(d(e))
        Float=source_fee('redeem',100.,100.+float(e),10.)
        w.writerow([e,str(D),str(R),repr(Float),repr(Float-float(R)),'REAL_MATH_ONLY'])
        if float(e)>=.00001:
         assert abs(source_fee('deposit',100.,100.+float(e),10.)-float(D)) < 1e-7
         if float(e)>=.001: assert abs(Float-float(R)) < 1e-9
    print('Independent high precision checks complete:',OUT)
