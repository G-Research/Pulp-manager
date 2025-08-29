# hashi_vault_client
Python client for interacting with Hahsicorp Vault.

This is a wrapper around the hvac client and has some specific function to it. Such
as getting service account passwords, rotating Linux root passwords and carrying out
an assume approle login

Separates out add and update methods in Hashicorp vault to protect from overwriting secrets if
they exist.

Is not designed to handle all features that hvac itself provides, if you need more advanced management then you should use the hvac module itself

# Usage

```
from hashi_vault_client.hashi_vault_client import HashiVaultClient
client = HashiVaultClient('http://localhost:8200', vault_agent=True)
client.list_kv_secrets()
```

# Development

```
create virtualenv, install dependencies and activate it

$ make venv
$ . venv/bin/activate

write code and unittests
run tests and lint as you progress
check tests coverage

$ make test
$ make lint
$ make cover

deactivate virtualenv and clean workspace when you are done

$ deactivate
$ make clean
```

# Create wheel file

```
$ python setup.py sdist bdist_wheel
$ ls -la dist/hashi_vault_client-*
```

