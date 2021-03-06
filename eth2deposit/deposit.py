import os
import sys
import click

from eth2deposit.credentials import (
    CredentialList,
)
from eth2deposit.exceptions import ValidationError
from eth2deposit.key_handling.key_derivation.mnemonic import (
    get_languages,
    get_mnemonic,
    _get_word_list,
)
from eth2deposit.utils.validation import verify_deposit_data_json
from eth2deposit.utils.constants import (
    WORD_LISTS_PATH,
    MAX_DEPOSIT_AMOUNT,
    DEFAULT_VALIDATOR_KEYS_FOLDER_NAME,
)
from eth2deposit.utils.ascii_art import RHINO_0
from eth2deposit.settings import (
    ALL_CHAINS,
    MAINNET,
    get_setting,
)

languages = get_languages(WORD_LISTS_PATH)


def generate_mnemonic(language: str, words_path: str) -> str:
    mnemonic = get_mnemonic(language=language, words_path=words_path)
    test_mnemonic = ''
    while mnemonic != test_mnemonic:
        click.clear()
        click.echo('This is your seed phrase. Write it down and store it safely, it is the ONLY way to retrieve your deposit.')  # noqa: E501
        click.echo('\n\n%s\n\n' % mnemonic)
        click.pause('Press any key when you have written down your mnemonic.')

        click.clear()
        test_mnemonic = click.prompt('Please type your mnemonic (separated by spaces) to confirm you have written it down\n\n')  # noqa: E501
        test_mnemonic = test_mnemonic.lower()
    click.clear()
    return mnemonic


def read_mnemonic(language: str, words_path: str) -> str:
    word_list = [w.strip() for w in _get_word_list(language, words_path)]
    mnemonic = 'foo'
    test_mnemonic = 'bar'
    while mnemonic != test_mnemonic:
        click.clear()
        mnemonic = click.prompt('Please type your mnemonic (separated by spaces)\n\n')  # noqa: E501
        mnemonic = mnemonic.lower()

        invalid_words = set([w for w in mnemonic.split(' ') if w not in word_list])
        if len(invalid_words) > 0:
            click.echo('The entered seed phrase contains the following invalid words: {}'.format(
                ', '.join(sorted(invalid_words))))
            click.pause('Press any key to try again.')
            continue

        if len(mnemonic.split(' ')) != 24:
            click.pause('The seed phrase must contain exactly 24 words. Press any key to try again.')
            continue

        click.clear()
        test_mnemonic = click.prompt('Please repeat your mnemonic (separated by spaces)\n\n')  # noqa: E501
        test_mnemonic = test_mnemonic.lower()
    click.clear()
    return mnemonic


def check_python_version() -> None:
    '''
    Checks that the python version running is sufficient and exits if not.
    '''
    if sys.version_info < (3, 7):
        click.pause('Your python version is insufficient, please install version 3.7 or greater.')
        sys.exit()


@click.command()
@click.option(
    '--num_validators',
    prompt='Please choose how many validators you wish to run',
    required=True,
    type=int,
)
@click.option(
    '--reuse_mnemonic',
    type=bool,
    default=False,
)
@click.option(
    '--mnemonic_language',
    prompt='Please choose your mnemonic language',
    type=click.Choice(languages, case_sensitive=False),
    default='english',
)
@click.option(
    '--folder',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=os.getcwd()
)
@click.option(
    '--chain',
    prompt='Please choose the (mainnet or testnet) network/chain name',
    type=click.Choice(ALL_CHAINS.keys(), case_sensitive=False),
    default=MAINNET,
)
@click.password_option(prompt='Type the password that secures your validator keystore(s)')
def main(num_validators: int, reuse_mnemonic : bool, mnemonic_language: str, folder: str, chain: str,
         password: str) -> None:
    check_python_version()
    if reuse_mnemonic:
        mnemonic = read_mnemonic(mnemonic_language, WORD_LISTS_PATH)
    else:
        mnemonic = generate_mnemonic(mnemonic_language, WORD_LISTS_PATH)
    amounts = [MAX_DEPOSIT_AMOUNT] * num_validators
    folder = os.path.join(folder, DEFAULT_VALIDATOR_KEYS_FOLDER_NAME)
    setting = get_setting(chain)
    if not os.path.exists(folder):
        os.mkdir(folder)
    click.clear()
    click.echo(RHINO_0)
    click.echo('Creating your keys.')
    credentials = CredentialList.from_mnemonic(
        mnemonic=mnemonic,
        num_keys=num_validators,
        amounts=amounts,
        fork_version=setting.GENESIS_FORK_VERSION,
    )
    click.echo('Saving your keystore(s).')
    keystore_filefolders = credentials.export_keystores(password=password, folder=folder)
    click.echo('Creating your deposit(s).')
    deposits_file = credentials.export_deposit_data_json(folder=folder)

    click.echo('Verifying your keystore(s).')
    if not credentials.verify_keystores(keystore_filefolders=keystore_filefolders, password=password):
        raise ValidationError("Failed to verify the keystores.")

    click.echo('Verifying your deposit(s).')
    if not verify_deposit_data_json(deposits_file):
        raise ValidationError("Failed to verify the deposit data JSON files.")

    click.echo('\nSuccess!\nYour keys can be found at: %s' % folder)
    click.pause('\n\nPress any key.')


if __name__ == '__main__':
    main()
