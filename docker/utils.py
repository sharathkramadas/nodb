# import docker
class DockerUtils:

    def __init__(self):
        pass

    def generate_docker_file(self, image):
        client = docker.from_env()
        lines = client.api.history(image)

        complete_file = ""

        for line in lines:
            created_by = line.get("CreatedBy", "")
            created_by = created_by.replace("/bin/sh -c ", "").replace("# buildkit", "").strip()
            complete_file += created_by + "\n\n"

        # Reverse lines to reconstruct Dockerfile in correct order
        complete_file = "\n".join(complete_file.splitlines()[::-1])

        return complete_file

    def build_image(self, os_name, os_version, package_name, package_version):
        IMAGE_NAME = "alpine"
        IMAGE_TAG = f"{os_version}"
        DOCKERFILE_PATH = "Dockerfile.temp"

        print(f"{IMAGE_NAME}:{IMAGE_TAG}")

        dockerfile_template = f"""
FROM docker.io/library/alpine:{os_version}
RUN apk update
RUN apk add {package_name}
"""

        with open(DOCKERFILE_PATH, "w") as f:
            f.write(dockerfile_template.strip() + "\n")

        print(f"Generated Dockerfile:\n{dockerfile_template}")

        client = docker.from_env()

        print(f"\nBuilding image {IMAGE_NAME}:{IMAGE_TAG}...")

        image, build_logs = client.images.build(
            path=".",
            dockerfile=DOCKERFILE_PATH,
            tag=f"{IMAGE_NAME}:{IMAGE_TAG}",
            rm=True,
        )

        # Print build logs
        for chunk in build_logs:
            if "stream" in chunk:
                print(chunk["stream"].strip())

        print("\nBuild complete ✅")
