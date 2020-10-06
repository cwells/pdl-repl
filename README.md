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
  search:
    size: 10
    pretty: True
```

Commands
========
> The REPL provides a multi-line buffer. As such, pressing `enter` will start a
new line, but _not_ execute the command or query. You must press `alt+enter` to
execute the command.

- `mode sql`

    Interact with search API using SQL mode for ElasticSearch queries.

- `mode es`

    Interact with search API using ES mode for ElasticSearch queries.

- `mode enrich`

    Interact with the enrichment API using query strings.

- `set <setting> <value>`

    Change configuration settings on-the-fly, e.g.
    ```
    set size 10
    ```

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
In this mode you provide the required parameters in the form of a URL query string:
```
email=cliff.wells@gmail.com&email=cliff@peopledatalabs.com
```

History
=======
History is stored separately for each mode under `~/.pdl-repl`.