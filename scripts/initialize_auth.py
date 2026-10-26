"""Initialize a private local Office login without putting credentials in source."""
from getpass import getpass
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth import OfficeAuth, MIN_PASSWORD_LENGTH


def main() -> None:
    path = Path(os.environ.get('OFFICE_AUTH_FILE', str(Path.home() / '.local/state/office/auth.json'))).expanduser()
    if path.exists():
        raise SystemExit('Authentication already exists; refusing to overwrite it.')
    username = input('Local Office username: ').strip()
    password = getpass('New local password: ')
    confirmation = getpass('Confirm password: ')
    if not username or password != confirmation or len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit('A username, matching passwords, and the minimum password length are required.')
    OfficeAuth(path).initialize(username, password, force_change=False)
    print('Local Office authentication initialized. No credentials were printed.')


if __name__ == '__main__':
    main()
