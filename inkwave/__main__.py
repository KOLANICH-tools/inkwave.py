from pathlib import Path

from plumbum import cli

from . import mainAPI


class MainCLI(cli.Application):
    """Convert a .wbf file to a .wrf file or if no output file is specified display human readable info about the specified .wbf or .wrf file."""

    USAGE = "inkwave file.wbf/file.wrf [-o output.wrf]"

    outfile_path = cli.SwitchAttr("-o", help="Specify output file")
    force_input = cli.SwitchAttr("-f", help="Force inkwave to interpret input file as either .wrf or .wbf format regardless of file extension")
    trace = cli.Flag("-t", help="Enable extended tracing needed for testing of identicity of the behavior of different impls.")

    def main(self, infile_path: str) -> int:
        return mainAPI(Path(infile_path), self.force_input, Path(self.outfile_path) if self.outfile_path else None, (2 if self.trace else 0))


if __name__ == "__main__":
    MainCLI.run()
