import json
import click
from pathlib import Path
from annotation_engine.vep_runner import run_vep
from annotation_engine.evidence_aggregator import gather_evidence
from annotation_engine.tiering import assign_tier

@click.command()
@click.argument("vcf", type=click.Path(exists=True))
@click.option("--cancer-type", required=True)
@click.option("--out", type=click.Path(), default="annotated.json")
def main(vcf, cancer_type, out):
    vep_json = run_vep(Path(vcf))
    ev = gather_evidence(vep_json, cancer_type)
    tiers = [assign_tier(item) for item in ev]
    Path(out).write_text(json.dumps([t.model_dump() for t in tiers], indent=2))

if __name__ == "__main__":
    main()
