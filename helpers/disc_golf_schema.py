import sqlalchemy as sa

schema = {
    "course":
        sa.table(
            "course",
            sa.Column("course_id", sa.Integer, primary_key=True),
            sa.Column("course_name", sa.Text),
            sa.Column("name", sa.Text),
            sa.Column("holes", sa.Integer),
            sa.Column("units", sa.Text),
        ),
    "player":
        sa.table(
            "player",
            sa.Column("pdga_number", sa.Integer, primary_key=True),
            sa.Column("first_name", sa.Text, nullable=False),
            sa.Column("last_name", sa.Text, nullable=False),
            sa.Column("state", sa.Text),
            sa.Column("city", sa.Text),
            sa.Column("country", sa.Text),
            sa.Column("division", sa.Text),
        ),
    "tournament":
        sa.table(
            "tournament",
            sa.Column("tournament_id", sa.Integer, primary_key=True),
            sa.Column("name", sa.Text, nullable=False),
            sa.Column("start_date", sa.Date, nullable=False),
            sa.Column("classification", sa.Text, nullable=False),
            sa.Column("director", sa.Text),
            sa.Column("is_worlds", sa.Boolean),
            sa.Column("total_rounds", sa.Integer, nullable=False),
        ),
    "round":
        sa.table(
            "round",
            sa.Column("round_id", sa.Integer, primary_key=True),
            sa.Column("tournament_id", sa.Integer, sa.ForeignKey("tournament.tournament_id"), nullable=False),
            sa.Column("tournament_round_num", sa.Integer, nullable=False),
            sa.Column("tee_time", sa.DateTime, nullable=False),
            sa.Column("course_id", sa.Integer, sa.ForeignKey("course.course_id"), nullable=False),
            sa.Column("pdga_number", sa.Integer, sa.ForeignKey("player.pdga_number"), nullable=False),
            sa.Column("score", sa.Integer),
            sa.Column("date", sa.Date),
        ),
    "hole":
        sa.table(
            "hole",
            sa.Column("hole_id", sa.Text, primary_key=True, nullable=False),
            sa.Column("layout_id", sa.Integer, nullable=False),
            sa.Column("course_id", sa.Integer, sa.ForeignKey("course.course_id"), nullable=False),
            sa.Column("round_id", sa.Integer, nullable=False),
            sa.Column("person_round_id", sa.Integer),
            sa.Column("pdga_number", sa.Integer, sa.ForeignKey("player.pdga_number"), nullable=False),
            sa.Column("tournament_round_num", sa.Integer),
            sa.Column("won_playoff", sa.Text),
            sa.Column("prize", sa.Text),
            sa.Column("round_status", sa.Text),
            sa.Column("hole_count", sa.Integer),
            sa.Column("card_number", sa.Integer),
            sa.Column("tee_time",  sa.Text),
            sa.Column("round_rating", sa.Integer),
            sa.Column("hole_number", sa.Integer, nullable=False),
            sa.Column("par", sa.Integer),
            sa.Column("length", sa.Integer),
            sa.Column("score", sa.Integer),
    )
}