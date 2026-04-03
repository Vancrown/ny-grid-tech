"""
pages/home.py — BorrowWatts home page
Dark hero landing page with the NYC building photo, centered "Borrow from Neighbours"
copy, and slim CTA tabs under the hero text.
"""

import dash
from dash import dcc, html

dash.register_page(__name__, path="/", name="Home")

layout = html.Div(
    className="bw-home-dark",
    children=[
        html.Section(
            className="bw-hero-dark",
            children=[
                html.Div(className="bw-hero-overlay"),
                html.Div(
                    className="bw-hero-inner",
                    children=[
                        html.Div("NYC'S ENERGY SHARING NETWORK", className="bw-hero-kicker"),
                        html.H1(
                            [
                                "Borrow Watts from ",
                                html.Span("Neighbours", className="bw-hero-accent"),
                            ],
                            className="bw-hero-title",
                        ),
                        html.P(

                            "BorrowWatt is an Energy-Optimization-as-a-Service platform that lets residents trade "
                            "excess electricity within their building — cutting bills, reducing grid strain, and "
                            "making clean energy actionable for everyone.",
                            # "BorrowWatts helps multifamily buildings share local solar and battery energy "
                            # "so residents can access cheaper, cleaner power before falling back on the grid.",
                            className="bw-hero-subtitle",
                        ),
                        html.Div(
                            className="bw-hero-tab-row",
                            children=[
                                dcc.Link(
                                    html.Div(
                                        [
                                            html.Div("Residents", className="bw-hero-tab-title"),
                                            # html.Div("Multifamily Owners", className="bw-hero-tab-subtitle"),
                                        ],
                                        className="bw-hero-tab bw-hero-tab-left",
                                    ),
                                    href="/how",
                                    className="bw-hero-tab-link",
                                ),
                                dcc.Link(
                                    html.Div(
                                        [
                                            html.Div(
                                                "Building Owners",
                                                className="bw-hero-tab-title",
                                            ),
                                            # html.Div("Battery Arbitrage", className="bw-hero-tab-subtitle"),
                                        ],
                                        className="bw-hero-tab bw-hero-tab-right",
                                    ),
                                    href="/battery",
                                    className="bw-hero-tab-link",
                                ),
                            ],
                        ),
                    ],
                ),

                html.Div("+8.4 kW", className="bw-kw-badge bw-kw-1"),
                html.Div("-3.1 kW", className="bw-kw-badge bw-kw-2"),
                html.Div("+12.0 kW", className="bw-kw-badge bw-kw-3"),
                html.Div("-1.9 kW", className="bw-kw-badge bw-kw-4"),
                html.Div("+5.0 kW", className="bw-kw-badge bw-kw-5"),
            ],
        ),
    ],
)
