'''
ESPPv2 Wrapper
'''

# pylint: disable=invalid-name

import logging
from enum import Enum
import typer
from espp2.main import do_taxes
from espp2.datamodels import TaxReport, Holdings, Wires
from espp2.report import print_report
from pydantic import parse_obj_as
import json
from numpy import nan

app = typer.Typer()

class BrokerEnum(str, Enum):
    '''BrokerEnum'''
    schwab = 'schwab'
    td = 'td'
    morgan = 'morgan'

logger = logging.getLogger(__name__)

from espp2._version import __version__
def version_callback(value: bool):
    if value:
        typer.echo(f"espp2 CLI Version: {__version__}")
        raise typer.Exit()
@app.command()
def main(transaction_files: list[typer.FileBinaryRead],
         output: typer.FileTextWrite = None,
         year: int = 2022,
         broker: BrokerEnum = BrokerEnum.schwab,
         wires: typer.FileText = None,
         inholdings: typer.FileText = None,
         outholdings: typer.FileTextWrite = None,
         outwires: typer.FileTextWrite = None,
         verbose: bool = False,
         opening_balance: str = None,
         loglevel: str = typer.Option("WARNING", help='Logging level'),
         version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True)):

    '''ESPPv2 tax reporting tool'''
    lognames = logging.getLevelNamesMapping()
    if loglevel not in lognames:
        raise typer.BadParameter(f'Invalid loglevel: {loglevel}')
    logging.basicConfig(level=lognames[loglevel])

    if opening_balance:
        opening_balance = json.loads(opening_balance)
        opening_balance = parse_obj_as(Holdings, opening_balance)

    holdings: Holdings
    result = do_taxes(broker, transaction_files, inholdings, wires, year, verbose=verbose, opening_balance=opening_balance)
    if isinstance(result, Holdings):
        holdings = result
    # report, holdings, summary = do_taxes(
    #     broker, transaction_files, inholdings, wires, year, verbose=verbose, opening_balance=opening_balance)
    else:
        print_report(year, result.summary, result.report, result.holdings, verbose)

    # New holdings
    if outholdings:
        logger.info('Writing new holdings to %s', outholdings.name)
        j = holdings.json(indent=4)
        with outholdings as f:
            f.write(j)
    if outwires and result.report.unmatched_wires:
        logger.info('Writing unmatched wires to %s', outwires.name)
        outw = Wires(__root__=result.report.unmatched_wires)
        for w in outw.__root__:
            w.nok_value = nan
            w.value = abs(w.value)
        j = outw.json(indent=4)
        with outwires as f:
            f.write(j)

    # Tax report (in JSON)
    if output:
        j = result.report.json(indent=4)
        logger.info('Writing tax report to: %s', output.name)
        with output as f:
            f.write(j)

if __name__ == '__main__':
    app()
