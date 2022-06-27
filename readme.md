# Token Package

Just contains various bits used across micro services

`python3 setup.py sdist bdist_wheel`

## How to use the search and filter module

In your graphql schema you can add the inputs variable that contains
several graphql inputs suitable to use for different data types

`full_schema = [load_schema_from_path("schema.graphql"), *inputs]`

**Example Input**

```graphql
input UuidFilterInput { 
    eq: Uuid neq: Uuid 
}
```

This input can be applied to UUID fields, so eq is equals and neq not equals, to match
the record from the database

**Graphql Schema**

In order to use this in the graphql schemas you need to create a filter input that
will contain these inputs that are created in the search and filter module

for example:

```graphql
input OrderBookingFilter {
  id: UuidFilterInput
  reference: StringFilterInput
  trackingNumber: IntegerFilterInput
  status: BookingStatus
  scheduled: DateTimeFilterInput
  created: DateTimeFilterInput
}
```

And if you want to use this as a query field you can like this:

```graphql
type Query {
  bookings(filter: OrderBookingFilter, search: String, first: Int, after: String): [OrderBooking]
}
```

This module comes with filter and search functionality, the search one just requires a String input and
Model that you want to do the search on, the results will be coming from `get_search_query(model, search)`.

The filter functionality comes from `get_filter_query(model, filter)`, filter is dictionary, like:
```graphql
filter = {
    "id": {
        "eq": "something",
    }
}
```

There's also a `ModelResolver` that accepts:
- formatter (the way model fields are displayed through graphql)
- model
- kwargs (this can be filter or search, plus the parameters required for the paginator)

After initiating this resolver you get:
- It will create RelayPaginator as a property accessible through `instance.paginator`.
- It creates base queryset using `Model.all()`, and if you call the `instance.get_data()` without specified qs it will return all the paginated records of the Model.
- You can override this base queryset inside the `instance.get_data(qs=YourQuerySet)` if needed. The output
of this method is paginated records of the Model.
- If the instance of the resolver contains filter or search in the extra fields then it will prioritise those ones and make the queryset use one of `get_search_query()` or `get_filter_query()`.

If you decide to use the ModelResolver's `get_data` method to get the data then the output of your function
will be a Connection type.

You can easily build your connection type using the graphql interfaces in this package.

The package comes with PageInfo type:

```graphql
type PageInfo {
    hasNextPage: Boolean!
    startCursor: String
    endCursor: String
}
```

And interfaces:

```graphql
interface Edge {
    cursor: String
}
interface Connection {
    pageInfo: PageInfo!
}
```

So you can use these interfaces in your graphql schema to build your types used for the RelayPaginator.
For example:

```graphql
type ModelEdge implements Edge {
    cursor: String
    node: Model
}

type ModelConnection implements Connection {
    pageInfo: PageInfo!
    edges: [ModelEdge]
}
```

## How to fix the workflows once search and filter module implemented.

#### Changes for Prod, Stage and Schema workflow

replace `- uses: actions/checkout@v2` with
```yaml
- name: Wait for tests
  uses: fountainhead/action-wait-for-check@v1.0.0
  id: wait-for-build
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    checkName: test
    ref: ${{ github.event.pull_request.head.sha || github.sha }}
    intervalSeconds: 20
- uses: actions/checkout@v2
- name: Download the graphql artifact
  if: steps.wait-for-build.outputs.conclusion == 'success'
  uses: dawidd6/action-download-artifact@v2
  with:
    workflow: python-app.yml
    workflow_conclusion: success
    name: output-schema-file
    path: ./lib_schema
```

replace `--localSchemaFile=./schema.graphql` with `--localSchemaFile=./schema.graphql,./lib_schema/schema.graphql `

#### Changes for Test workflow

ensure the file that contains the __test__ is called `python-app.yaml`

add the following above steps  
```yaml
env:
  PYTHON_VERSION: 3.8
```

alter the `Set up Python 3.8` step to be the following
```yaml
- name: Set up Python 3.8
  uses: actions/setup-python@v2
  with:
    python-version: ${{ env.PYTHON_VERSION }}
```

Finally, add the following step to the end
```yaml
- name: Upload Libary Schema
  uses: actions/upload-artifact@v1
  with:
    name: output-schema-file
    path: ${{ env.LD_LIBRARY_PATH }}/python${{ env.PYTHON_VERSION }}/site-packages/aj_micro_utils/search_and_filter/schema.graphql
```