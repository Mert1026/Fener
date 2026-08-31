import typer

app = typer.Typer(help="Fener ingestion and local administration", no_args_is_help=True)


@app.command()
def version() -> None:
    """Show the local platform version."""
    typer.echo("Fener 0.1.0")
