import sqlalchemy as sa

schema = {
    "courses": {
        sa.table(
            "course",
            sa.Column("course_id", sa.Integer, primary_key=True),
            sa.Column("course_name", sa.Text),
            sa.Column("name", sa.Text),
            sa.Column("holes", sa.Integer),
            sa.Column("par", sa.Integer),
            sa.Column("length", sa.Integer),
            sa.Column("units", sa.Text),
        )
    }
}