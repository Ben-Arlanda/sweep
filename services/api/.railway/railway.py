"""Railway settings for the API (ADR 0034). Preview: `uv run railway config plan`."""

from railway_sdk import define_railway, github, project, service, volume

# Only the API is managed here; the database and all variables stay in the dashboard.
PARTIAL = "sweep"
SINGAPORE = "asia-southeast1-eqsg3a"


@define_railway
def main(ctx=None):
    sweep = service(
        "sweep",
        # checkSuites: deploy a main commit only after its GitHub checks pass.
        source=github(
            "Ben-Arlanda/sweep",
            branch="main",
            checkSuites=True,
            rootDirectory="/services/api",
        ),
        build={"buildEnvironment": "V3", "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile"},
        healthcheck="/health",
        healthcheckTimeout=300,  # the container migrates before it serves
        replicas={SINGAPORE: 1},  # Singapore; one copy (one volume)
        # Member photos (PHOTO_DIR); region and size stated so IaC never resets them.
        volumeMounts={"/data": volume("sweep-volume", region=SINGAPORE, sizeMB=500)},
    )
    return project("sweep", variables={"managed": False}, resources=[sweep])
