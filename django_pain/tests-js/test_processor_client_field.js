import test from 'ava'
import { load_processor_client_field } from '../static/django_pain/js/es6/processor_client_field'

import 'node-fetch'
const fetchMock = require('fetch-mock/es5/server')

const TEST_PAGE = `
    <div class="field-processor">
        <div>
            <label>Processor:</label>
            <select id="id_processor" name="processor">
                <option name="DummyProcessor" selected>DummyProcessor</option>
            </select>
        </div>
    </div>
    <div class="field-client_id">
        <div>
            <label>Client ID:</label>
            <input type="text" name="client_id" />
        </div>
    </div>`

fetchMock.config.overwriteRoutes = true

test('Test not found', async t => {
    document.body.innerHTML = TEST_PAGE
    fetchMock.get('/ajax/processor_client_choices/?processor=DummyProcessor', 404)
    await load_processor_client_field()

    t.regex(document.querySelector('div.field-client_id div').innerHTML,
        /<input name="client_id" type="text">/)
})

test('Test render client choices', async t => {
    document.body.innerHTML = TEST_PAGE
    fetchMock.get('/ajax/processor_client_choices/?processor=DummyProcessor',
        {'TNG': 'The Next Generation', 'DS9': 'Deep space 9'})
    await load_processor_client_field()

    t.regex(document.querySelector('div.field-client_id div').innerHTML, new RegExp(
        '<select name="client_id"><option value="TNG">The Next Generation</option>' +
        '<option value="DS9">Deep space 9</option></select>'))
})
