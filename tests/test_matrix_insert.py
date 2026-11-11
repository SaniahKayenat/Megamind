"""First-valid reading and duplicate counts at the raw-to-matrix boundary."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pipeline_lib import insert_readings


def test_null_then_valid_inside_chunk_and_later_chunk():
    m=np.full((1,3),np.nan,dtype=np.float32); seen=np.zeros(m.shape,bool)
    dup,same=insert_readings(m,seen,[0,0,0],[0,0,1],[np.nan,.4,np.nan])
    assert dup==1 and same==0
    assert m[0,0]==np.float32(.4) and np.isnan(m[0,1])
    dup,same=insert_readings(m,seen,[0,0,0],[0,1,2],[.9,.2,.7])
    assert dup==2 and same==0
    assert np.array_equal(m,np.array([[.4,.2,.7]],dtype=np.float32))


def test_exact_duplicate_and_null_duplicate_are_counted():
    m=np.full((2,2),np.nan,dtype=np.float32); seen=np.zeros(m.shape,bool)
    dup,same=insert_readings(m,seen,[0,0,1,1],[0,0,1,1],[.3,.3,np.nan,np.nan])
    assert dup==2 and same==2
    dup,same=insert_readings(m,seen,[0,1],[0,1],[.3,np.nan])
    assert dup==2 and same==2
