import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Plotting.plot_funcs as pf
from KeyEventParser import vkconvert
import numpy as np

ddd = np.load('../hkm_data.npy', allow_pickle=True)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='Dash Test App'),

    html.Div(children='''
             Dash: a web application framework for Python.
             '''),
    dcc.Input(id='my-id', value='initial value', type='text'),
    html.Div(id='my-div'),
    dcc.Graph(
        id='tgplot',
        style={
            'height': 800
        },
        figure=pf.plot_tri_matrix(ddd, vkconvert)
    ),

    # dcc.Graph(
    #    id='example-graph',
    #    figure = {
    #        'data': [
    #            {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
    #            {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
    #        ],
    #        'layout': {
    #            'title': 'Dash Data Visualization'
    #        }
    #    }
    # )
])


@app.callback(
    Output(component_id='my-div', component_property='children'),
    [Input(component_id='my-id', component_property='value')]
)
def update_output_div(input_value):
    return 'You\'ve entered "{}"'.format(input_value)


if __name__ == '__main__':
    app.run_server(debug=True)
