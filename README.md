Installation
==============
```
python -m venv /path/to/venv
source path/to/venv/bin/activate
python -m pip install -r requirements.txt
```

> Note: copy-to-clipboard feature requires `xclip` package on Linux.

Configuration
=============
You need a YAML configuration file located at `~/.pdl-repl/config.yaml` with
the following content:
```yaml
---
api_key: <your api key>

repl:
  mode: sql
  editor: vi
  search:
    size: 10
    pretty: True
```

Commands
========
The REPL provides a multi-line buffer. As such, pressing `enter` will start a
new line, but _not_ execute the command or query. You must press `alt+enter` to
execute the command.

> The REPL uses readline, so general readline features are available,
 e.g. `ctrl+r` searches backwards in the history.
When using `vi` mode, commands must be prefixed with `esc`.


- `set mode sql`

    Interact with search API using SQL mode for ElasticSearch queries.

- `set mode es`

    Interact with search API using ES mode for ElasticSearch queries.

- `set mode enrich`

    Interact with the enrichment API. Queries are passed as JSON.

- `set search.size <int>`

    Set size of return set, e.g.
    ```
    set search.size 10
    ```

- `set search.offset <int>`

    Set pagination offset , e.g.
    ```
    set search.offset 100
    ```

- `set editor [emacs|vi]`

    Set keybindings.

- `copy`

    Copies the last query result to the clipboard.

- `ctrl+d`

    Exit the REPL.


Queries
=======
SQL mode
--------
```sql
SELECT * FROM person WHERE job_company_name='people data labs'
```

ES mode
-------
```json
{
    "query": {
        "term": {
            "job_company_name": "people data labs"
        }
    }
}
```

Enrich mode
-----------
In this mode you provide the required parameters in JSON form:
```json
{
    "email": ["cliff@peopledatalabs.com", "cliff.wells@gmail.com"],
    "region": ["Oregon"]
}
```

History
=======
History is stored separately for each mode under `~/.pdl-repl`.