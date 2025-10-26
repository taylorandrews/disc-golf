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
            sa.Column("player_id", sa.Integer, primary_key=True),
            sa.Column("name", sa.Text, nullable=False),
            sa.Column("state", sa.Text),
            sa.Column("dob", sa.Date),
        ),
    "tournament":
        sa.table(
            "tournament",
            sa.Column("tournament_id", sa.Integer, primary_key=True),
            sa.Column("name", sa.Text, nullable=False),
            sa.Column("year", sa.Integer),
            sa.Column("classification", sa.Text),
            sa.Column("total_rounds", sa.Integer),
            sa.Column("cutoff_score", sa.Integer),
            sa.Column("cutoff_day", sa.Text),
        ),
    "round":
        sa.table(
            "round",
            sa.Column("round_id", sa.Integer, primary_key=True),
            sa.Column("tournament_id", sa.Integer, sa.ForeignKey("tournament.tournament_id"), nullable=False),
            sa.Column("tournament_round_num", sa.Integer, nullable=False),
            sa.Column("tee_time", sa.DateTime, nullable=False),
            sa.Column("course_id", sa.Integer, sa.ForeignKey("course.course_id"), nullable=False),
            sa.Column("player_id", sa.Integer, sa.ForeignKey("player.player_id"), nullable=False),
            sa.Column("score", sa.Integer),
            sa.Column("date", sa.Date),
        ),
    "hole":
        sa.table(
            "hole",
            sa.Column("hole_id", sa.Integer, primary_key=True),
            sa.Column("course_id", sa.Integer, sa.ForeignKey("course.course_id"), nullable=False),
            sa.Column("round_id", sa.Integer, sa.ForeignKey("round.round_id"), nullable=False),
            sa.Column("hole_number", sa.Integer, nullable=False),
            sa.Column("par", sa.Integer),
            sa.Column("distance", sa.Integer),
            sa.Column("score", sa.Integer),
    )
}