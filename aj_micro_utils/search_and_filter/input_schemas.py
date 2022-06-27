string_filter_input = """
    input StringFilterInput {
    matches: String
    eq: String
    neq: String
    contains: String
    icontains: String
    }
"""

uuid_filter_input = """
    input UuidFilterInput {
    eq: Uuid
    neq: Uuid
    in: [Uuid]
    }
"""

boolean_filter_input = """
    input BoolFilterInput {
    eq: Boolean
    }
"""

datetime_filter_input = """
    input DateTimeFilterInput {
    gt: Datetime
    lt: Datetime
    gte: Datetime
    lte: Datetime
    eq: Datetime
    neq: Datetime
    }
"""

integer_filter_input = """
    input IntegerFilterInput {
    gt: Int
    lt: Int
    gte: Int
    lte: Int
    eq: Int
    neq: Int
    }
"""

page_info = """
    type PageInfo {
        hasNextPage: Boolean!
        startCursor: String
        endCursor: String
    }
"""

edge_interface = """
    interface Edge {
        cursor: String
    }
"""

connection_interface = """
    interface Connection {
        pageInfo: PageInfo!
    }
"""

inputs = [
    string_filter_input,
    uuid_filter_input,
    boolean_filter_input,
    datetime_filter_input,
    integer_filter_input,
    page_info,
    edge_interface,
    connection_interface,
]
