from subprocess import Popen
import os
import logging
import time

from chimera.util.sextractor import SExtractor
from chimera.core.exceptions import ChimeraException
from chimera.util.image import Image

log = logging.getLogger(__name__)


class AstrometryNet:
    # staticmethod allows to use a single method of a class
    @staticmethod
    def solve_field(full_filename, find_star_method="astrometry.net"):
        """
        @param: full_filename entire path to image
        @type: str

        @param: find_star_method (astrometry.net, sex)
        @type: str

        Does astrometry to image=full_filename
        Uses either astrometry.net or sex(tractor) as its star finder
        """

        pathname, filename = os.path.split(full_filename)
        pathname = pathname + "/"
        basefilename, file_xtn = os.path.splitext(filename)
        # *** enforce .fits extension
        if file_xtn != ".fits":
            raise ValueError(f"File extension must be .fits it was = {file_xtn}\n")

        # *** check whether the file exists or not
        if os.path.exists(full_filename) == False:
            raise IOError(f"You selected image {full_filename}  It does not exist\n")

        # version 0.23 changed behavior of --overwrite
        # I need to specify an output filename with -o
        outfilename = basefilename + "-out"

        image = Image.from_file(full_filename)
        try:
            ra = image["CRVAL1"]  # expects to see this in image
        except:
            raise AstrometryNetException("Need CRVAL1 on header")
        try:
            dec = image["CRVAL2"]
        except:
            raise AstrometryNetException("Need CRVAL2 on header")
        width = image["NAXIS1"]
        height = image["NAXIS2"]
        if "CD1_1" in image:
            radius = 10.0 * abs(image["CD1_1"]) * width
        else:
            radius = 1.0  # default radius if no CD1_1 found (degrees)

        wcs_filename = pathname + outfilename + ".wcs"

        if find_star_method == "astrometry.net":
            line = f"solve-field {full_filename} --no-plots --overwrite -o {outfilename} --ra {ra:f} --dec {dec:f} --radius {radius:f}"
        elif find_star_method == "sex":
            sexoutfilename = pathname + outfilename + ".xyls"
            line = (
                f"solve-field {sexoutfilename} --no-plots --overwrite -o {outfilename} --x-column X_IMAGE --y-column Y_IMAGE "
                f"--sort-column MAG_ISO --sort-ascending --width {width:d} --height {height:d} --ra {ra:f} --dec {dec:f} --radius {radius:f}"
            )

            sex = SExtractor()
            sex.config["BACK_TYPE"] = "AUTO"
            sex.config["DETECT_THRESH"] = 3.0
            sex.config["DETECT_MINAREA"] = 18.0
            sex.config["VERBOSE_TYPE"] = "QUIET"
            sex.config["CATALOG_TYPE"] = "FITS_1.0"
            sex.config["CATALOG_NAME"] = sexoutfilename
            sex.config["PARAMETERS_LIST"] = ["X_IMAGE", "Y_IMAGE", "MAG_ISO"]
            sex.run(full_filename)

        else:
            log.error("Unknown option used in astrometry.net")

        # when there is a solution astrometry.net creates a file with .solved
        # added as extension.
        is_solved = pathname + outfilename + ".solved"
        # if it is already there, make sure to delete it
        if os.path.exists(is_solved):
            os.remove(is_solved)
        log.debug(f"SOLVE {line}")
        # *** it would be nice to add a test here to check
        # whether astrometrynet is running OK, if not raise a new exception
        # like AstrometryNetInstallProblem
        log.debug("Starting solve-field...")
        t0 = time.time()
        solve = Popen(line.split())  # ,env=os.environ)
        solve.wait()
        log.debug(f"Solve field finished. Took {time.time() - t0:3.2f} sec")
        # if solution failed, there will be no file .solved
        if os.path.exists(is_solved) == False:
            raise NoSolutionAstrometryNetException(
                f"Astrometry.net could not find a solution for image: {full_filename} {is_solved}"
            )

        return wcs_filename


class AstrometryNetException(ChimeraException):
    pass


class NoSolutionAstrometryNetException(ChimeraException):
    pass
