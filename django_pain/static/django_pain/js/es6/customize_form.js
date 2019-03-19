/**
 * Asynchronously load processors options.
 */
export async function load_processors_options() {
    const response = await fetch('/ajax/get_processors_options/')
    if (response.status === 200) {
        const response_json = await response.json()
        return response_json
    } else {
        return {}
    }
}

/**
 * Modify form based on processor options.
 *
 * @param {Object} options
 * @param {string} processor
 *
 * - hide manual tax date field unless processor supports it
 */
export function customize_form(options, processor) {
    const tax_date_field = document.querySelector('div.field-tax_date')
    if (options[processor] && options[processor].manual_tax_date === true)
        tax_date_field.style.display = 'block'
    else
        tax_date_field.style.display = 'none'
}

document.addEventListener('DOMContentLoaded', async function() {
    const options = await load_processors_options()
    const processor_field = document.querySelector('#id_processor')
    customize_form(options, processor_field.options[processor_field.selectedIndex].value)
    processor_field.addEventListener('change', () => {
        const processor = processor_field.options[processor_field.selectedIndex].value
        customize_form(options, processor)
    })
})
