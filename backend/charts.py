from __future__ import annotations

import base64
import io
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# Optional plotly imports
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def _save_matplotlib_figure(fig: matplotlib.figure.Figure) -> str:
    """Convert matplotlib figure to base64-encoded PNG JSON string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)
    return json.dumps({"image": img_base64, "type": "matplotlib"})


def empty_chart(use_plotly: bool = False) -> str:
    if use_plotly:
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is not installed. Install with: pip install plotly")
        fig = go.Figure()
        fig.update_layout(title="No visualization available")
        return fig.to_json()
    else:
        fig = plt.figure()
        plt.text(0.5, 0.5, "No visualization available", ha="center", va="center")
        plt.axis("off")
        return _save_matplotlib_figure(fig)


def generate_chart(
    tool_name: str,
    result: dict,
    use_plotly: bool = False
):

    try:

        if not result:
            return empty_chart(use_plotly=use_plotly)

        if tool_name == "get_population_trends":
            return population_trends_chart(result, use_plotly=use_plotly)

        if tool_name == "get_country_key_figures":
            return key_figures_chart(result, use_plotly=use_plotly)

        if tool_name == "get_demographic_breakdown":
            return demographic_chart(result, use_plotly=use_plotly)

        if tool_name == "get_population_data":
            return population_chart(result, use_plotly=use_plotly)

        return empty_chart(use_plotly=use_plotly)

    except Exception:
        return empty_chart(use_plotly=use_plotly)


def population_trends_chart(
    result: dict,
    use_plotly: bool = False
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
        return empty_chart(use_plotly=use_plotly)

    df = pd.DataFrame(rows)

    if use_plotly:
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is not installed. Install with: pip install plotly")
        fig = px.line(
            df,
            x="year",
            y="value",
            color="population_type",
            markers=True,
            title=result.get("country", "Population Trends")
        )
        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Population"
        )
        return fig.to_json()
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        for pop_type in df["population_type"].unique():
            subset = df[df["population_type"] == pop_type]
            ax.plot(subset["year"], subset["value"], marker="o", label=pop_type)
        ax.set_xlabel("Year")
        ax.set_ylabel("Population")
        ax.set_title(result.get("country", "Population Trends"))
        ax.legend()
        ax.grid(True, alpha=0.3)
        return _save_matplotlib_figure(fig)


def key_figures_chart(
    result: dict,
    use_plotly: bool = False
):

    breakdown = result.get(
        "breakdown",
        []
    )

    if not breakdown:
        return empty_chart(use_plotly=use_plotly)

    df = pd.DataFrame(breakdown)

    if use_plotly:
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is not installed. Install with: pip install plotly")
        fig = px.pie(
            df,
            names="population_type",
            values="count",
            title=f"{result.get('country')} Population Breakdown"
        )
        return fig.to_json()
    else:
        fig, ax = plt.subplots(figsize=(8, 8))
        labels = df["population_type"].tolist()
        values = df["count"].tolist()
        colors = plt.cm.tab20.colors
        ax.pie(values, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
        ax.set_title(f"{result.get('country')} Population Breakdown")
        return _save_matplotlib_figure(fig)


def demographic_chart(
    result: dict,
    use_plotly: bool = False
):

    data = result.get(
        "demographics",
        []
    )

    if not data:
        return empty_chart(use_plotly=use_plotly)

    df = pd.DataFrame(data)

    if use_plotly:
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is not installed. Install with: pip install plotly")
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
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        if "sex" in df.columns:
            sexes = df["sex"].unique().tolist()
            colors = {"Male": "#1f77b4", "Female": "#ff7f0e", "Other": "#2ca02c"}
            age_groups = df["age_group"].unique().tolist()
            width = 0.8 / len(sexes)
            
            for i, sex in enumerate(sexes):
                subset = df[df["sex"] == sex].sort_values("age_group")
                y = subset["count"].tolist()
                x_pos = [j + i * width for j in range(len(age_groups))]
                ax.bar(x_pos, y, width=width, label=sex, color=colors.get(sex, "gray"))
            
            ax.set_xticks([j + width * (len(sexes) - 1) / 2 for j in range(len(age_groups))])
            ax.set_xticklabels(age_groups)
        else:
            ax.bar(df["age_group"], df["count"])
        ax.set_xlabel("Age Group")
        ax.set_ylabel("Population")
        ax.set_title(f"{result.get('country')} Demographics")
        ax.legend()
        return _save_matplotlib_figure(fig)


def population_chart(
    result: dict,
    use_plotly: bool = False
):

    # UNHCR API returns data under 'items', not 'data'
    data = result.get(
        "items",
        result.get("data", [])
    )

    if not data:
        return empty_chart(use_plotly=use_plotly)

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
            return empty_chart(use_plotly=use_plotly)

        label_col = None
        for col in ["population_type", "coo_name", "coa_name"]:
            if col in df.columns:
                label_col = col
                break
        if not label_col:
            label_col = df.columns[0]

        if use_plotly:
            if not PLOTLY_AVAILABLE:
                raise ImportError("plotly is not installed. Install with: pip install plotly")
            fig = px.bar(
                df,
                x=label_col,
                y=value_col,
                title="UNHCR Population Data"
            )
            return fig.to_json()
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(df[label_col], df[value_col])
            ax.set_title("UNHCR Population Data")
            ax.set_xlabel(label_col)
            ax.set_ylabel(value_col)
            return _save_matplotlib_figure(fig)

    df = pd.DataFrame(rows)

    country_name = rows[0]["country"] if rows else "Unknown"

    if use_plotly:
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is not installed. Install with: pip install plotly")
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
    else:
        color_map = {
            "Refugees": "#0072BC",
            "Asylum Seekers": "#6CD8FD",
            "Idps": "#32C189",
            "Stateless": "#FFC740",
            "Oip": "#D25A45",
            "Ooc": "#A097E3",
            "Hst": "#BFBFBF",
            "Returned Refugees": "#00B398",
            "Returned Idps": "#00B398",
        }
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(df["population_type"], df["value"], 
               color=[color_map.get(t, "gray") for t in df["population_type"]])
        ax.set_title(f"{country_name} — Population of Concern")
        ax.set_xlabel("Population Type")
        ax.set_ylabel("Number of People")
        plt.xticks(rotation=45, ha="right")
        return _save_matplotlib_figure(fig)


def chart_from_dataframe(
    df: pd.DataFrame,
    chart_type: str = "bar",
    x: str | None = None,
    y: str | None = None,
    color: str | None = None,
    title: str | None = None,
    use_plotly: bool = False
):

    if use_plotly:
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is not installed. Install with: pip install plotly")
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
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        if chart_type == "line":
            for col in (df[color].unique() if color else [None]):
                subset = df[df[color] == col] if color else df
                ax.plot(subset[x], subset[y], marker="o", label=col if color else None)
            if color:
                ax.legend()
        elif chart_type == "pie":
            ax.pie(df[y], labels=df[x], autopct="%1.1f%%", startangle=90)
        else:
            if color:
                for col_val in df[color].unique():
                    subset = df[df[color] == col_val]
                    ax.bar(subset[x], subset[y], label=col_val)
                ax.legend()
            else:
                ax.bar(df[x], df[y])
        if title:
            ax.set_title(title)
        ax.set_xlabel(x if x else "")
        ax.set_ylabel(y if y else "")
        return _save_matplotlib_figure(fig)