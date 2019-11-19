const path = require('path')
const webpack = require('webpack')

module.exports = {
    mode: 'production',
    entry: {
        state_colors: path.resolve(__dirname, 'django_pain/static/django_pain/js/es6/state_colors.js'),
        processor_client_field: [
            'babel-polyfill',
            path.resolve(__dirname, 'django_pain/static/django_pain/js/es6/processor_client_field.js'),
        ],
        edit_confirmation: path.resolve(__dirname, 'django_pain/static/django_pain/js/es6/edit_confirmation.js'),
        customize_form: path.resolve(__dirname, 'django_pain/static/django_pain/js/es6/customize_form.js'),
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
        rules: [{
            test: /\.js$/,
            include: path.join(__dirname, 'django_pain/static/django_pain/js/es6'),
            exclude: /node_modules/,
            use: ['babel-loader'],
        }],
    },
}
