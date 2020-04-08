import 'babel-polyfill'
import 'jquery'
import fetchMock from 'fetch-mock'
import flushPromises from 'flush-promises'
import { load_processor_client_field } from '../static/django_pain/js/es6/processor_client_field'

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

describe('processor_client_field', () => {

    it('Test not found', async() => {
        document.body.innerHTML = TEST_PAGE
        fetchMock.get('/ajax/processor_client_choices/?processor=DummyProcessor', 404)
        await load_processor_client_field()
        await flushPromises()

        expect(document.querySelector('div.field-client_id div').innerHTML)
            .toContain('<input name="client_id" type="text">')
    })

    it('Test render client choices', async() => {
        global.jQuery = () => {
            return {
                select2: () => {},
            }
        }
        document.body.innerHTML = TEST_PAGE
        fetchMock.get('/ajax/processor_client_choices/?processor=DummyProcessor',
            {'TNG': 'The Next Generation', 'DS9': 'Deep space 9'})
        await load_processor_client_field()
        await flushPromises()

        expect(document.querySelector('div.field-client_id div').innerHTML)
            .toMatch(new RegExp(
                '<select name="client_id"[^>]*>' +
                '<option value="DS9">Deep space 9</option>' +
                '<option value="TNG">The Next Generation</option>' +
                '</select>'),
            )
    })
})
