

from chimera.util.position import Position
from chimera_pverify.util.catalogs.landolt import Landolt


class TestLandolt (object):

    def test_find (self):

        landolt = Landolt()
        landolt.use_target(Position.fromRaDec("14:00:00","-22:00:00"),radius=45)
        landolt.constrain_columns({"Vmag":"<10"})

        data = landolt.find(limit=5)

        for obj in data:
            for k,v in list(obj.items()):
                assert k
                assert v
                print((k, v))

    # def test_find_none (self):
    #
    #     landolt = Landolt()
    #     #landolt.useTarget(Position.fromRaDec("14:00:00","-22:00:00"),radius=45)
    #     landolt.constrainColumns({"Vmag":"<10"})
    #
    #     assert_raises(AssertionError, landolt.find, limit=5)

