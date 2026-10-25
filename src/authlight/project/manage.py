import os
import sys


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) > 1 and argv[1] == "init":
        from authlight.project.initialize import main as init_main

        init_main(argv[2:])
        return
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "authlight.project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
