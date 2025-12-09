# chimera-pverify plugin

Plugin for automatically verify (and correct) the pointing of telescopes using chimera and Astrometry.net.

This is a plugin for the [Chimera observatory control system](https://github.com/astroufsc/chimera).

## Usage

Install this plugin and add it as a controller to your `chimera.config` file. Then, follow the instructions given by `chimera-pverify --help`.

## Installation

This plugin depends on [SExtractor](http://www.astromatic.net/software/sextractor) and Astrometry.net's `solve-field` command line tool working with the necessary astrometry databases.

For more info on installing astrometry.net: http://astrometry.net/use.html

```bash
pip install -U git+https://github.com/astroufsc/chimera-pverify.git
```

## Configuration Example

Add the following to your `chimera.config` file:

```yaml
controllers:
  - type: PointVerify
    name: pv
    telescope: /FakeTelescope/fake      # Telescope to verify pointing.
    camera: /FakeCamera/fake            # Camera attached to the telescope.
    filterwheel: /FakeCamera/fake       # Filterwheel, if exists.
    exptime: 10.0                       # Exposure time.
    filter: R                           # Filter to expose.
    max_fields: 100                     # Maximum number of Landolt fields to use.
    max_tries: 5                        # Maximum number of tries to point the telescope correctly.
    dec_tolerance: 0.0167               # Maximum declination error tolerance (degrees).
    ra_tolerance: 0.0167                # Maximum right ascension error tolerance (degrees).
```





## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/wschoenell/chimera-pverify.git
cd chimera-pverify

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install --install-hooks
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

This project uses:
- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [pre-commit](https://pre-commit.com/) for automated checks

```bash
# Run linter
uv run ruff check

# Run formatter
uv run ruff format

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## License

MIT

## Contact

For more information, contact us on chimera's discussion list:
https://groups.google.com/forum/#!forum/chimera-discuss

Bug reports and patches are welcome and can be sent over our GitHub page:
https://github.com/astroufsc/chimera-pverify/
