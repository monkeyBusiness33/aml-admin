from django.db import connections


def update_database_sequences(database: str = 'default'):
    connection = connections[database]
    cursor = connection.cursor()

    # Generate sequence update statement for each database table
    cursor.execute(
        f'''
            SELECT 'SELECT SETVAL(' ||
                 quote_literal(quote_ident(PGT.schemaname) || '.' || quote_ident(S.relname)) ||
                 ', COALESCE(MAX(' ||quote_ident(C.attname)|| '), 1) ) FROM ' ||
                 quote_ident(PGT.schemaname)|| '.'||quote_ident(T.relname)|| ';'
            FROM pg_class AS S,
                 pg_depend AS D,
                 pg_class AS T,
                 pg_attribute AS C,
                 pg_tables AS PGT
            WHERE S.relkind = 'S'
                 AND S.oid = D.objid
                 AND D.refobjid = T.oid
                 AND D.refobjid = C.attrelid
                 AND D.refobjsubid = C.attnum
                 AND T.relname = PGT.tablename
            ORDER BY S.relname;
         '''
    )

    all_tables_statements = cursor.fetchall()

    for table_statement in all_tables_statements:
        try:
            table_statement_query = table_statement[0]
            cursor.execute(table_statement_query)
        except IndexError:
            pass

    # Commit changes
    connection.commit()
