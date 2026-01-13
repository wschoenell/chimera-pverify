import os
import time
from math import fabs

from chimera.core.chimeraobject import ChimeraObject
from chimera.core.exceptions import CantPointScopeException, ChimeraException
from chimera.interfaces.camera import Shutter
from chimera.interfaces.pointverify import PointVerify
from util.astrometrynet import AstrometryNet, NoSolutionAstrometryNetException
from chimera.util.coord import Coord
from chimera.util.image import ImageUtil, Image
from chimera.util.position import Position


class PointVerify(ChimeraObject, PointVerify):
    """
    Verifies telescope pointing.
    There are two ways of doing this:
       - verify the field the scope has been pointed to
       - choose a field (from a list of certified fields) and try verification
    """

    # normal constructor
    # initialize the relevant variables
    def __init__(self):
        ChimeraObject.__init__(self)
        self.ntrials = 0  # number times we try to center on a field
        self.nfields = 0  # number of fields we try to center on
        self.checkedpointing = False  # True = Standard field is verified
        self.current_field = 0  # counts fields tried to verify

    def get_tel(self):
        return self.get_proxy(self["telescope"])

    def get_cam(self):
        return self.get_proxy(self["camera"])

    def get_filter_wheel(self):
        return self.get_proxy(self["filterwheel"])
    
    def get_site(self):
        return self.get_proxy("/Site/0")

    def get_rotator(self):
        if self["rotator"] is not None:
            return self.get_proxy(self["rotator"])
        else:
            return None

    def _take_image(self, image_request):

        cam = self.get_cam()
        if cam["telescope_focal_length"] is None:
            raise ChimeraException("telescope_focal_length parameter must be set on camera instrument configuration")
        if self["filterwheel"] is not None:
            fw = self.get_filter_wheel()
            fw.set_filter(self["filter"])

        request = dict(exptime=self["exptime"], frames=1, shutter=Shutter.OPEN,
                       filename=os.path.basename(ImageUtil.make_filename("pointverify-$DATE")))
        request.update(image_request)
        frames = cam.expose(**request)

        if frames:
            image = Image.from_url(frames[0])
            if not os.path.exists(image.filename):  # If image is on a remote server, donwload it.

                # #  If remote is windows, image_path will be c:\...\image.fits, so use ntpath instead of os.path.
                # if ':\\' in image_path:
                #     modpath = ntpath
                # else:
                #     modpath = os.path
                # image_path = ImageUtil.make_filename(os.path.join(self["images_dir"], "$LAST_NOON_DATE", modpath.basename(image_path)))
                t0 = time.time()
                self.log.debug(f'Downloading image from server to {image.filename}')
                if not image.download():
                    raise ChimeraException(f'Error downloading image {image.filename} from {image.http()}')
                self.log.debug(f'Finished download. Took {time.time() - t0:3.2f} seconds')
            return image.filename, image
        else:
            raise Exception("Could not take an image")

    def point_verify(self, image_request={}):
        """
        Checks telescope pointing.
        If abs ( telescope coordinates - image coordinates ) > tolerance
           move the scope
           take a new image
           test again
           do this while ntrials < max_tries

        Returns True if centering was succesful
                False if not
        """

        # take an image and read its coordinates off the header

        try:
            image_path, image = self._take_image(image_request)
            self.log.debug(f"Taking image: image name {image_path}")
        except:
            self.log.error("Can't take image")
            raise

        tel = self.get_tel()
        # analyze the previous image using
        # AstrometryNet defined in util
        try:
            wcs_name = AstrometryNet.solve_field(image_path, find_star_method="sex")
        except NoSolutionAstrometryNetException as e:
            raise e
            # why can't I select this exception?
            #
            # there was no solution to this field.
            # send the telescope back to checkPointing
            # if that fails, clouds or telescope problem
            # an exception will be raised there
            # self.log.error("No WCS solution")
            # if not self.checkedpointing:
            #    self.nfields += 1
            #    self.currentField += 1
            #    if self.nfields <= self["max_fields"] and self.checkPointing() == True:
            #        self.checkedpointing = True
            #        tel.slewToRaDec(currentImageCenter)
            #        try:
            #            self.pointVerify()
            #            return True
            #        except CanSetScopeButNotThisField:
            #            raise
            #
            #    else:
            #        self.checkedpointing = False
            #        self.currentField = 0
            #        raise Exception("max fields")
            #
            # else:
            #    self.checkedpointing = False
            #    raise CanSetScopeButNotThisField(f"Able to set scope, but unable to verify this field {currentImageCenter}")
        wcs_image = Image.from_file(wcs_name)
        ra_wcs_center, dec_wcs_center = wcs_image.world_at((image["NAXIS1"] / 2., image["NAXIS2"] / 2.))
        rotation = wcs_image.get_rotation()
        self.log.debug(f"WCS rotation: {rotation:f} degrees")
        current_wcs = Position.from_ra_dec(Coord.from_d(ra_wcs_center), Coord.from_d(dec_wcs_center))

        # save the position of first trial:
        if self.ntrials == 0:
            ra_img_center = image["CRVAL1"]  # expects to see this in image
            dec_img_center = image["CRVAL2"]
            current_image_center = Position.from_ra_dec(Coord.from_d(ra_img_center),
                                                    Coord.from_d(dec_img_center))
            self._original_center = current_image_center
            self._original_ra = ra_img_center
            self._original_dec = dec_img_center
            self.log.debug(f"Setting ra, dec for {ra_img_center}, {dec_img_center}")

            initial_position = Position.from_ra_dec(
                Coord.from_d(ra_img_center), Coord.from_d(dec_img_center))
        else:
            current_image_center = self._original_center
            ra_img_center = self._original_ra
            dec_img_center = self._original_dec
            self.log.debug("Using previous ra, dec.")

        # write down the two positions for later use in mount models
        if self.ntrials == 0:
            site = self.get_site()
            logstr = f"Pointing Info for Mount Model: {site.lst()} {site.mjd()} {image['DATE-OBS']} {initial_position} {current_wcs}"
            self.log.info(logstr)

        delta_ra = ra_img_center - ra_wcs_center
        delta_dec = dec_img_center - dec_wcs_center

        # *** need to do real logging here
        logstr = f"{image['DATE-OBS']} ra_tel = {ra_img_center} dec_tel = {dec_img_center} ra_img = {ra_wcs_center} dec_img = {dec_wcs_center} delta_ra = {delta_ra} delta_dec = {delta_dec}"
        self.log.debug(logstr)

        if (fabs(delta_ra) > self["ra_tolerance"]) or (fabs(delta_dec) > self["dec_tolerance"]):
            self.log.debug("Telescope not there yet. Trying again")
            self.ntrials += 1
            if self.ntrials > self["max_tries"]:
                self.ntrials = 0
                raise CantPointScopeException(
                    f"Scope does not point with a precision of {self['ra_tolerance']} (RA) or {self['dec_tolerance']} (DEC) after {self['max_tries']:d} trials\n")
            tel.move_offset(Coord.from_d(delta_ra).arcsec, Coord.from_d(delta_dec).arcsec)
            self.point_verify()
        else:
            # if we got here, we were succesfull, reset trials counter
            self.ntrials = 0
            self.current_field = 0
            # and save final position
            # write down the two positions for later use in mount models
            logstr = f"Final solution: {image['DATE-OBS']} {current_image_center} {current_wcs}"
            # self.log.debug(f"Synchronizing telescope on {currentWCS}")
            # tel.syncRaDec(currentWCS)

            # *** should we sync the scope ???
            # maybe there should be an option of syncing or not
            # the first pointing in the night should sync I believe
            # subsequent pointings should not.
            # another idea is to sync if the delta_coords at first trial were
            # larger than some value
            self.log.info(logstr)

        if self["rotator"] is not None:
            self.log.info(f"Field rotation is {rotation:f} degrees, moving rotator.")
            self.get_rotator().move_by(-rotation)

        return True

    # def set_current_field(self, f):
    #     self.current_field = f
    #     return True

    # def check_pointing(self, nfields=1):
    #     """
    #     This method *chooses* a field to verify the telescope pointing.
    #     Then it does the pointing and verifies it.
    #     If unsuccesfull e-mail the operator for help

    #     Choice is based on some catalog (Landolt here)
    #     We choose the field closest to zenith
    #     """
    #     # find where the zenith is
    #     site = self.getManager().getProxy("/Site/0")
    #     lst = site.LST()
    #     lat = site["latitude"]
    #     coords = Position.fromRaDec(lst, lat)

    #     self.log.info(f"Check pointing - Zenith coordinates: {lst:f} {lat:f}")

    #     tel = self.get_tel()

    #     # use the Vizier catalogs to see what Landolt field is closest to
    #     # zenith
    #     self.log.debug("Calling landolt")
    #     fld = Landolt()
    #     fld.useTarget(coords, radius=45)
    #     obj = fld.find(limit=self["max_fields"])

    #     self.log.debug(f"Objects returned from Landolt: {obj}")
    #     # get ra, dec to call pointVerify
    #     ra = obj[self.current_field]["RA"]
    #     dec = obj[self.current_field]["DEC"]
    #     name = obj[self.current_field]["ID"]
    #     self.log.debug(f"Current object: {ra}, {dec}, {name}")

    #     self.log.info(f"Chose {name} {ra:f} {dec:f}")
    #     tel.slewToRaDec(Position.fromRaDec(ra, dec))
    #     try:
    #         self.point_verify()
    #     except Exception as e:
    #         print_exception(e)
    #         raise CantSetScopeException(
    #             f"Can't set scope on field {name} {ra:f} {dec:f} we are in trouble, call for help")
    #     return True

    # def findStandards(self):
    #     """
    #     Not yet implemented.
    #     The idea is to find the best standard field to do automatic setting of
    #     the telescope coordinates.
    #     It seems that for telescopes > 40cm Landolt fields suffice.
    #     For scopes < 40 cm on bright skies we may need to build a list of
    #     compact open clusters.
    #     """
    #     site = self.getManager().getProxy("/Site/0")
    #     lst = site.LST()
    #     # *** need to come from config file
    #     min_mag = 6.0
    #     max_mag = 11.0
    #     self.searchStandards(lst - 3, lst + 3, min_mag, max_mag)

    # def searchStandards(self, min_ra, max_ra, min_mag, max_mag):
    #     """
    #     Searches a catalog of standards for good standards to use
    #     They should be good for focusing, pointing and extinction

    #     @param min_ra: minimum RA of observable standard
    #     @type  min_ra: L{float}

    #     @param max_ra: maximum RA of observable standard
    #     @type  max_ra: L{float}

    #     @param min_mag: minimum magnitude of standard
    #     @type  min_mag: L{float}

    #     @param max_mag: maximum magnitude of standard
    #     @type  max_mag: L{float}

    #     should return a list of standard stars within the limits
    #     """


if __name__ == "__main__":
    x = PointVerify()
    # x.checkPointing()
    x.point_verify()
