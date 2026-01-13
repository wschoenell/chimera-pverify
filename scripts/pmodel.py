import datetime
from chimera_pverify.util.astrometrynet import AstrometryNet, NoSolutionAstrometryNetException
from pathlib import Path
from astropy.io import fits
from chimera.util.position import Position, Coord
from chimera.core.site import Site

data_folder = "/Users/william/Downloads/swope_data/20251208/"
output_fname = "pmodel_astrometry_results.csv"

data_path = Path(data_folder)
fits_files = list(data_path.glob("*.fits")) + list(data_path.glob("*.fit"))

site = Site()
site["name"] = "Swope"
site["latitude"] = "-29:00:43"
site["longitude"] = "-70:42:01"
site["altitude"] = 2187

pmhelper_files = []
for fits_file in fits_files:
    with fits.open(fits_file) as hdul:
        header = hdul[0].header
        if "OBJECT" in header and header["OBJECT"] is not None and header["OBJECT"].endswith("_pmhelper"):
            pmhelper_files.append(fits_file)
pmhelper_files.sort()

print(f"Found {len(pmhelper_files)} files with '_pmhelper' in OBJECT keyword")

fout = open(output_fname, "w")
fout.write("Star RA,Star Dec,Scope RA,Scope Dec,LST,Date_Obs,Filename\n")
for f in pmhelper_files:
    print(f"Solving astrometry for file: {f}")
    try:
        # initial image
        h = fits.getheader(f)
        ra_img_center = h["CRVAL1"]  # expects to see this in image
        dec_img_center = h["CRVAL2"]
        initial_image_center = Position.from_ra_dec(Coord.from_d(ra_img_center), Coord.from_d(dec_img_center))
        date_obs = datetime.datetime.strptime(h["DATE-OBS"], "%Y-%m-%dT%H:%M:%S.%f")
        lst = site.lst(date_obs)
        print(f"Site {site['latitude']}, {site['longitude']}, LST: {lst}")
        st = h["ST"]  # in seconds

        # solved image
        wcs_name = AstrometryNet.solve_field(str(f), find_star_method="sex")
        h = fits.getheader(wcs_name)
        ra_img_center = h["CRVAL1"]  # expects to see this in image
        dec_img_center = h["CRVAL2"]
        solved_image_center = Position.from_ra_dec(Coord.from_d(ra_img_center), Coord.from_d(dec_img_center))
        print(f"Pointing model: {initial_image_center}, Solved center: {solved_image_center}")
        fout.write(
            f"{str(solved_image_center).replace(' ', ',')},{str(initial_image_center).replace(' ', ',')},{lst},{date_obs},{f}\n"
        )
        print(f"st: {lst}, {Coord.from_h(st/3600).to_hms()}")
        fout.flush()
        print(f"Successfully solved astrometry for {f}")
    except NoSolutionAstrometryNetException:
        print(f"No solution found for {f}")
        fout.write(f"# {f}: No solution found\n")
    except Exception as e:
        print(f"Error solving astrometry for {f}: {e}")
    # break  # --- REMOVE THIS LINE TO PROCESS ALL FILES ---

fout.close()
