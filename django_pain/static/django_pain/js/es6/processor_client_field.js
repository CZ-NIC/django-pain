/* global django: true, jQuery: true */

/* Expose global jQuery because of Select2 library */
if (jQuery === undefined && django !== undefined) {
    jQuery = django.jQuery
}

/**
 * Load available client choices from chosen payment processor.
 *
 * Loaded choices are displayed in select box.
 * If none are provided, simple text input is displayed instead.
 */
export async function load_processor_client_field() {
    const processor_field = document.querySelector('#id_processor')
    const processor = processor_field.options[processor_field.selectedIndex].value

    const response = await fetch('/ajax/processor_client_choices/?processor=' + processor)
    const client_id_field = document.querySelector('div.field-client_id div')
    if (response.status === 200) {
        // Construct select box from received choices
        response.json().then(data => {
            let selectbox = '<select name="client_id" id="select_client_id">'
            Object.keys(data).sort((a, b) => data[a].localeCompare(data[b])).forEach(key => {
                selectbox += `<option value="${key}">${data[key]}</option>`
            })
            selectbox += '</select>'
            client_id_field.innerHTML = client_id_field.innerHTML.replace(
                /<\/label>[^]*/, '</label>' + selectbox)
            jQuery('#select_client_id').select2()
        })
    } else {
        // Render default text input widget
        client_id_field.innerHTML = client_id_field.innerHTML.replace(
            /<\/label>[^]*/, '</label><input name="client_id" type="text">')
    }
}

document.addEventListener('DOMContentLoaded', function() {
    load_processor_client_field()
    const processor_field = document.querySelector('#id_processor')
    processor_field.addEventListener('change', load_processor_client_field)
})
