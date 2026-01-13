from chimera.util.position import Position
from chimera_pverify.util.vizquery import VizQuery


class TestVizQuery (object):

    def test_find (self):
        x = VizQuery()
        x.use_cat("II/183A/")
        x.use_columns("*POS_EQ_RA_MAIN,*POS_EQ_DEC_MAIN,*ID_MAIN,Vmag,_r",
                     sort_by="*POS_EQ_RA_MAIN")
        x.use_target(Position.fromRaDec("14:00:00","-22:00:00"),radius=45)
        
        data = x.find(limit=5)

        for obj in data:
            for k,v in list(obj.items()):
                print((k, v))
            print()
