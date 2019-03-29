import 'babel-polyfill'
import 'jquery'
import fetchMock from 'fetch-mock'
import { customize_form, load_processors_options } from '../static/django_pain/js/es6/customize_form'

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
    </div>
    <div class="field-tax_date">
        <div>
            <label>Tax date:</label>
            <input type="text" name="tax_date" />
        </div>
    </div>`

fetchMock.config.overwriteRoutes = true

describe('customize form', () => {

    it('should show tax_date', () => {
        document.body.innerHTML = TEST_PAGE
        customize_form({DummyProcessor: {manual_tax_date: true}}, 'DummyProcessor')
        expect(document.querySelector('div.field-tax_date').style.display)
            .toBe('block')
    })

    it('should show tax_date', () => {
        document.body.innerHTML = TEST_PAGE
        customize_form({DummyProcessor: {manual_tax_date: false}}, 'DummyProcessor')
        expect(document.querySelector('div.field-tax_date').style.display)
            .toBe('none')
    })

    it('should load processors options', async() => {
        fetchMock.get('/ajax/get_processors_options/', {
            proc1: {manual_tax_date: true},
            proc2: {manual_tax_date: false},
        })
        const options = await load_processors_options()
        expect(options).toEqual({
            proc1: {manual_tax_date: true},
            proc2: {manual_tax_date: false},
        })
    })

    it('should handle error while loading processors options', async() => {
        fetchMock.get('/ajax/get_processors_options/', 404)
        const options = await load_processors_options()
        expect(options).toEqual({})
    })
})
