import argparse
import datetime
from pathlib import Path

# we keep the exact script used in our experiments for reproducibility,
# but we found that we need to add the following line before `RUN setup_<repo_name>.sh` to fix dependency versions when using poetry
# this is because poetry ignores the PIP_INDEX_URL environment variable and uses the default PyPI index unless specified in pyproject.toml.
# this affects the results in the following way:
# 1. newer versions of dependencies were installed in the old container, missing potential candidates that cause migration issues with intended versions.
# 2. versions used in the new container may slightly differ from those intended to be used as of the target date, leading to some false positives.
# we have only one problem using poetry in our Verified subset, and we confirmed that the problem is valid under the intended dependency versions.

# ```
# RUN printf '\n[[tool.poetry.source]]\nname = "mirror"\nurl = "http://localhost:5000/snapshot/{target_date}"\npriority = "primary"\n' >> pyproject.toml
# ```

DOCKERFILE_TEMPLATE = """
FROM mirror.gcr.io/python:{python_version}

ENV PIP_INDEX_URL=http://localhost:5000/snapshot/{target_date}
ENV PIP_TRUSTED_HOST=localhost

WORKDIR /work

COPY {repo_name_id} .

RUN bash /work/setup_{repo_name_id}.sh

ENTRYPOINT ["bash"]
CMD ["/work/test_{repo_name_id}.sh"]
""".strip()

def date_type(s: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e) + " Date must be in yyyy-mm-dd format.")

def main(args):
    repo_name_id = args.repo_name_id
    save_dir_root = args.save_dir_root

    target_version = args.target_version
    target_date = args.target_date

    dockerfile_str = DOCKERFILE_TEMPLATE.format(
        python_version=target_version,
        repo_name_id=repo_name_id,
        target_date=target_date.strftime("%Y-%m-%d")
    )

    with open(f"{save_dir_root}/{repo_name_id}.Dockerfile", "w") as f_out:
        print(dockerfile_str, file=f_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='add python version to use for reproduction')
    parser.add_argument('--repo_name_id', type=str, required=True, help="the name of the repository with slashes replaced by double underscores")
    parser.add_argument('--save_dir_root', type=Path, required=True, help="the directory to save dockerfiles")
    parser.add_argument('--target_version', type=str, required=True, help="target Python version to use in the container (use inferred version if not provided)")
    parser.add_argument('--target_date', type=date_type, required=True, help="target date until which specific python version must be released (use commit date if not provided)")

    args = parser.parse_args()
    main(args)
