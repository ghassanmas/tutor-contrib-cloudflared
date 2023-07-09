from __future__ import annotations

import os
import os.path
from glob import glob
import subprocess

import click
import pkg_resources
import appdirs

from tutor import hooks
from tutor import config
from tutor import fmt
from tutor.commands.context import Context
from tutor.utils import execute
from tutor.__about__ import __app__

from .__about__ import __version__
from .utils import check_ns, strip_out_subdomains_if_needed, is_default_domain, is_same_domain, is_one_or_less_subdomain, get_first_level_domain
from .constants import CLOUDFLARE_NS_SETUP_URL, TUTOR_PUBLIC_HOSTS
from .cli import cloudflared as cloudfalred_group
from .cli import get_tunnel_uuid
########################################
# CONFIGURATION
########################################

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Add your new settings that have default values here.
        # Each new setting is a pair: (setting_name, default_value).
        # Prefix your setting names with 'CLOUDFLARED_'.
        ("CLOUDFLARED_VERSION", __version__),
        ("CLOUDFLARED_DOCKER_IMAGE", "cloudflared"),
        ("CLOUDFLARED_TUNNEL_NAME", "openedx"),
        ("CLOUDFLARED_TUNNEL_UUID", ""),
        ("CLOUDFLARED_PUBLIC_HOSTS", TUTOR_PUBLIC_HOSTS)
    ]
)




########################################
# INITIALIZATION TASKS
########################################

# # To add a custom initialization task, create a bash script template under:
# # tutorcloudflared/templates/cloudflared/jobs/init/
# # and then add it to the MY_INIT_TASKS list. Each task is in the format:
# # ("<service>", ("<path>", "<to>", "<script>", "<template>"))
# MY_INIT_TASKS: list[tuple[str, tuple[str, ...]]] = [
#     # For example, to add LMS initialization steps, you could add the script template at:
#     # tutorcloudflared/templates/cloudflared/jobs/init/lms.sh
#     # And then add the line:
#     # ("lms", ("cloudflared", "jobs", "init", "lms.sh")),
#     ("cloudflared", ("cloudflared", "tasks", "cloudflared", "init"))
# ]


# # For each task added to MY_INIT_TASKS, we load the task template
# # and add it to the CLI_DO_INIT_TASKS filter, which tells Tutor to
# # run it as part of the `init` job.
# MY_INIT_TASKS: list[tuple[str, tuple[str, ...]]] = [
#     # For example, to add LMS initialization steps, you could add the script template at:
#     # tutorcloudflared/templates/cloudflared/jobs/init/lms.sh
#     # And then add the line:
#     # ("lms", ("cloudflared", "jobs", "init", "lms.sh")),
#     ("cloudflared", ("cloudflared", "tasks", "cloudflared", "init")),
# ]


with open(
    pkg_resources.resource_filename(
        "tutorcloudflared", os.path.join(
            "templates", "cloudflared", "tasks", "cloudflared", "init")
    ),
    encoding="utf8",
) as f:
    hooks.Filters.CLI_DO_INIT_TASKS.add_item(("cloudflared", f.read()))


# For each task added to MY_INIT_TASKS, we load the task template
# and add it to the CLI_DO_INIT_TASKS filter, which tells Tutor to
# run it as part of the `init` job.
    # Now you have init_task, you may want to add it to CLI_DO_INIT_TASKS or perform other actions.


########################################
# DOCKER IMAGE MANAGEMENT
########################################


# Images to be built by `tutor images build`.
# Each item is a quadruple in the form:
#     ("<tutor_image_name>", ("path", "to", "build", "dir"), "<docker_image_tag>", "<build_args>")
hooks.Filters.IMAGES_BUILD.add_items(
    [
        # To build `myimage` with `tutor images build myimage`,
        # you would add a Dockerfile to templates/cloudflared/build/myimage,
        # and then write:
        (
            "cloudflared",
            ("plugins", "cloudflared", "build", "cloudflared"),
            "{{ CLOUDFLARED_DOCKER_IMAGE }}",
            (),
        ),
    ]
)


# Images to be pulled as part of `tutor images pull`.
# Each item is a pair in the form:
#     ("<tutor_image_name>", "<docker_image_tag>")
hooks.Filters.IMAGES_PULL.add_items(
    [
        # To pull `myimage` with `tutor images pull myimage`, you would write:
        # (
        # "myimage",
        # "docker.io/myimage:{{ CLOUDFLARED_VERSION }}",
        # ),
    ]
)


# Images to be pushed as part of `tutor images push`.
# Each item is a pair in the form:
#     ("<tutor_image_name>", "<docker_image_tag>")
hooks.Filters.IMAGES_PUSH.add_items(
    [
        # To push `myimage` with `tutor images push myimage`, you would write:
        # (
        # "myimage",
        # "docker.io/myimage:{{ CLOUDFLARED_VERSION }}",
        # ),
    ]
)


########################################
# TEMPLATE RENDERING
# (It is safe & recommended to leave
#  this section as-is :)
########################################

hooks.Filters.ENV_TEMPLATE_ROOTS.add_items(
    # Root paths for template files, relative to the project root.
    [
        pkg_resources.resource_filename("tutorcloudflared", "templates"),
    ]
)

hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    # For each pair (source_path, destination_path):
    # templates at ``source_path`` (relative to your ENV_TEMPLATE_ROOTS) will be
    # rendered to ``source_path/destination_path`` (relative to your Tutor environment).
    # For example, ``tutorcloudflared/templates/cloudflared/build``
    # will be rendered to ``$(tutor config printroot)/env/plugins/cloudflared/build``.
    [
        ("cloudflared/build", "plugins"),
        ("cloudflared/apps", "plugins"),
    ],
)


########################################
# PATCH LOADING
# (It is safe & recommended to leave
#  this section as-is :)
########################################

# For each file in tutorcloudflared/patches,
# apply a patch based on the file's name and contents.
for path in glob(
    os.path.join(
        pkg_resources.resource_filename("tutorcloudflared", "patches"),
        "*",
    )
):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item(
            (os.path.basename(path), patch_file.read()))


def iter_domains():
    root = appdirs.user_data_dir(__app__)
    print(root)
    configs = config.load(root)
    domains = dict(zip(configs.get('CLOUDFLARED_PUBLIC_HOSTS'), [configs.get(
        host) for host in TUTOR_PUBLIC_HOSTS if configs.get(host) is not None]))
    yield from domains.items()


hooks.Filters.ENV_TEMPLATE_VARIABLES.add_item(("iter_domains", iter_domains))

########################################
# CUSTOM JOBS (a.k.a. "do-commands")
########################################

# A job is a set of tasks, each of which run inside a certain container.
# Jobs are invoked using the `do` command, for example: `tutor local do importdemocourse`.
# A few jobs are built in to Tutor, such as `init` and `createuser`.
# You can also add your own custom jobs:


# @click.command()
# def some_set() -> list[tuple[str, str]]:
#     """
#     An example job that just prints 'hello' from within both LMS and CMS.
#     """
#     for task in MY_INIT_TASKS:
#         init_task: str = get_task_contents(task)
#         return [("cloudflared", "cloudflared tunnel info -o json openedx | jq -rc '.id'")]


# To add a custom job, define a Click command that returns a list of tasks,
# where each task is a pair in the form ("<service>", "<shell_command>").
# For example:


hooks.Filters.CLI_DO_COMMANDS.add_item(get_tunnel_uuid)


#######################################
# CUSTOM CLI COMMANDS
#######################################

# Your plugin can also add custom commands directly to the Tutor CLI.
# These commands are run directly on the user's host computer
# (unlike jobs, which are run in containers).

# To define a command group for your plugin, you would define a Click
# group and then add it to CLI_COMMANDS:
hooks.Filters.CLI_COMMANDS.add_item(cloudfalred_group)





# Then, you would add subcommands directly to the Click group, for example:
