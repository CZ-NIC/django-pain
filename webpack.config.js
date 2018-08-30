const path = require('path')
const webpack = require('webpack')
const UglifyJsPlugin = require('uglifyjs-webpack-plugin')

module.exports = {
    entry: {
        state_colors: path.resolve(__dirname, 'django_pain/static/django_pain/js/es6/state_colors.js'),
        processor_client_field: [
            'babel-polyfill',
            path.resolve(__dirname, 'django_pain/static/django_pain/js/es6/processor_client_field.js'),
        ],
    },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'django_pain/static/django_pain/js'),
    },
    devtool: 'source-map',
    devServer: {
        contentBase: path.resolve(__dirname, 'django_pain/static/django_pain/js'),
    },
    module: {
        loaders: [{
            test: /\.js$/,
            include: path.join(__dirname, 'django_pain/static/django_pain/js/es6'),
            exclude: /node_modules/,
            loaders: ['babel-loader'],
        }],
    },
    plugins: [
        new UglifyJsPlugin({
            sourceMap: true,
            uglifyOptions: { compress: { warnings: false } },
        }),
    ],
}