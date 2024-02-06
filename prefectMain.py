import httpx
from prefect import flow


@flow(log_prints=True)
def get_repo_info(repo_name: str = "PrefectHQ/prefect"):
    url = f"https://api.github.com/repos/{repo_name}"
    response = httpx.get(url)
    response.raise_for_status()
    repo = response.json()
    print(f"{repo_name} repository statistics 🤓:")
    print(f"Stars 🌠 : {repo['stargazers_count']}")
    print(f"Forks 🍴 : {repo['forks_count']}")


if __name__ == "__main__":
    get_repo_info.from_source(
        source="https://github.com/discdiver/demos.git", 
        entrypoint="repo_info.py:get_repo_info"
    ).deploy(
        name="my-first-deployment", 
        work_pool_name="my-managed-pool", 
    )

# import time
# from prefect import flow, serve


# @flow
# def slow_flow(sleep: int = 60):
#     "Sleepy flow - sleeps the provided amount of time (in seconds)."
#     time.sleep(sleep)


# @flow
# def fast_flow():
#     "Fastest flow this side of the Mississippi."
#     return


# if __name__ == "__main__":
#     slow_deploy = slow_flow.to_deployment(name="sleeper", interval=45)
#     fast_deploy = fast_flow.to_deployment(name="fast")
#     serve(slow_deploy, fast_deploy)
