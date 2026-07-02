from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def empty_chart():

    fig = go.Figure()

    fig.update_layout(
        title="No visualization available"
    )

    return fig.to_json()


def generate_chart(
    tool_name: str,
    result: dict
):

    try:

        if not result:
            return empty_chart()

        if tool_name == "get_population_trends":
            return population_trends_chart(result)

        if tool_name == "get_country_key_figures":
            return key_figures_chart(result)

        if tool_name == "get_demographic_breakdown":
            return demographic_chart(result)

        if tool_name == "get_population_data":
            return population_chart(result)

        return empty_chart()

    except Exception:
        return empty_chart()


def population_trends_chart(
    result: dict
):

    time_series = result.get(
        "time_series",
        {}
    )

    rows = []

    for year, values in time_series.items():

        for pop_type, value in values.items():

            rows.append(
                {
                    "year": int(year),
                    "population_type": pop_type,
                    "value": value
                }
            )

    if not rows:
        return empty_chart()

    df = pd.DataFrame(rows)

    fig = px.line(
        df,
        x="year",
        y="value",
        color="population_type",
        markers=True,
        title=result.get(
            "country",
            "Population Trends"
        )
    )

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Population"
    )

    return fig.to_json()


def key_figures_chart(
    result: dict
):

    breakdown = result.get(
        "breakdown",
        []
    )

    if not breakdown:
        return empty_chart()

    df = pd.DataFrame(breakdown)

    fig = px.pie(
        df,
        names="population_type",
        values="count",
        title=f"{result.get('country')} Population Breakdown"
    )

    return fig.to_json()


def demographic_chart(
    result: dict
):

    data = result.get(
        "demographics",
        []
    )

    if not data:
        return empty_chart()

    df = pd.DataFrame(data)

    fig = px.bar(
        df,
        x="age_group",
        y="count",
        color="sex",
        barmode="group",
        title=f"{result.get('country')} Demographics"
    )

    fig.update_layout(
        xaxis_title="Age Group",
        yaxis_title="Population"
    )

    return fig.to_json()


def population_chart(
    result: dict
):

    # UNHCR API returns data under 'items', not 'data'
    data = result.get(
        "items",
        result.get("data", [])
    )

    if not data:
        return empty_chart()

    # The API returns wide-format data with separate columns
    # for each population type (refugees, asylum_seekers, etc.)
    pop_type_cols = [
        "refugees",
        "asylum_seekers",
        "stateless",
        "idps",
        "returned_refugees",
        "returned_idps",
        "ooc",
        "oip",
        "hst",
    ]

    # Build rows by melting population type columns
    rows = []
    for item in data:
        country = (
            item.get("coa_name") or
            item.get("coo_name") or
            "Unknown"
        )
        for col in pop_type_cols:
            val = item.get(col)
            if val is not None and val != "0" and val != "-":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    continue
                if val > 0:
                    label = col.replace("_", " ").title()
                    rows.append({
                        "population_type": label,
                        "value": val,
                        "country": country,
                    })

    if not rows:
        # Fallback: try generic column detection
        df = pd.DataFrame(data)
        value_col = None
        for col in ["value", "population", "count"]:
            if col in df.columns:
                value_col = col
                break
        if not value_col:
            return empty_chart()

        label_col = None
        for col in ["population_type", "coo_name", "coa_name"]:
            if col in df.columns:
                label_col = col
                break
        if not label_col:
            label_col = df.columns[0]

        fig = px.bar(
            df,
            x=label_col,
            y=value_col,
            title="UNHCR Population Data"
        )
        return fig.to_json()

    df = pd.DataFrame(rows)

    country_name = rows[0]["country"] if rows else "Unknown"

    fig = px.bar(
        df,
        x="population_type",
        y="value",
        color="population_type",
        title=f"{country_name} — Population of Concern",
        color_discrete_map={
            "Refugees": "#0072BC",
            "Asylum Seekers": "#6CD8FD",
            "Idps": "#32C189",
            "Stateless": "#FFC740",
            "Oip": "#D25A45",
            "Ooc": "#A097E3",
            "Hst": "#BFBFBF",
            "Returned Refugees": "#00B398",
            "Returned Idps": "#00B398",
        },
    )

    fig.update_layout(
        xaxis_title="Population Type",
        yaxis_title="Number of People",
        showlegend=False,
    )

    return fig.to_json()


def chart_from_dataframe(
    df: pd.DataFrame,
    chart_type: str = "bar",
    x: str | None = None,
    y: str | None = None,
    color: str | None = None,
    title: str | None = None
):

    if chart_type == "line":

        fig = px.line(
            df,
            x=x,
            y=y,
            color=color,
            title=title
        )

    elif chart_type == "pie":

        fig = px.pie(
            df,
            names=x,
            values=y,
            title=title
        )

    else:

        fig = px.bar(
            df,
            x=x,
            y=y,
            color=color,
            title=title
        )

    return fig.to_json()