import subprocess
import sys
import typer
import httpx

app = typer.Typer(help="Groundwork — learn from your code")
API_BASE = "http://localhost:8000"


@app.command()
def diff():
    """Analyse concepts in your uncommitted git diff."""
    result = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True)
    code = result.stdout
    if not code.strip():
        typer.echo("No changes to analyse.")
        raise typer.Exit()
    _post_and_print(code)


@app.command()
def analyse(path: str = typer.Argument(..., help="Path to a Python file")):
    """Analyse concepts in a specific file."""
    try:
        code = open(path).read()
    except FileNotFoundError:
        typer.echo(f"File not found: {path}", err=True)
        raise typer.Exit(1)
    _post_and_print(code)


@app.command()
def concepts():
    """Show your full knowledge graph."""
    res = httpx.get(f"{API_BASE}/concepts")
    data = res.json()
    for c in data["concepts"]:
        bar = "█" * int(c["confidence"] * 10)
        typer.echo(f"{c['id']:30} {bar:<10} {c['confidence']:.2f}")


@app.command()
def digest():
    """Show today's session digest."""
    res = httpx.get(f"{API_BASE}/session/digest")
    data = res.json()
    typer.echo(f"Concepts seen today: {data['concepts_seen']}")
    if data["new_concepts"]:
        typer.echo("New: " + ", ".join(c["id"] for c in data["new_concepts"]))
    if data["gaps"]:
        typer.echo("Gaps: " + ", ".join(c["id"] for c in data["gaps"]))


def _post_and_print(code: str):
    res = httpx.post(f"{API_BASE}/analyse", json={"code": code, "language": "python"})
    data = res.json()

    if data.get("skipped"):
        typer.echo("Nothing new to learn here.")
        return

    typer.echo(f"\nConcept: {data['novel_concept']}\n")
    typer.echo(data["explanation"])
    typer.echo(f"\nChallenge: {data['challenge_question']}\n")


if __name__ == "__main__":
    app()
