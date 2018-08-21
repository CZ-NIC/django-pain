import test from 'ava'
import { color_rows_by_state } from '../static/django_pain/js/es6/state_colors'

const TEST_PAGE = `
    <table id="result_list">
        <thead>...</thead>
        <tbody>
            <tr class="row1">
                <th class="field-identifier"><a href="#">11112222</a></th>
                <td class="field-account_number">123456/0300</td>
                <td class="field-state_styled"><div class="state_deferred">deferred</div></td>
            </tr>
            <tr class="row2">
                <th class="field-identifier"><a href="#">22223333</a></th>
                <td class="field-account_number">123456/0300</td>
                <td class="field-state_styled"><div class="state_processed">processed</div></td>
            </tr>
            <tr class="row3">
                <th class="field-identifier"><a href="#">33331111</a></th>
                <td class="field-account_number">123456/0300</td>
                <td class="field-state_styled">imported</td>
            </tr>
        </tbody>
    </table>`

test('Color rows by state', t => {
    document.body.innerHTML = TEST_PAGE
    color_rows_by_state()

    let row = document.querySelector('tr.row1')
    t.true(row.classList.contains('payment_deferred'))
    t.false(row.classList.contains('payment_processed'))

    row = document.querySelector('tr.row2')
    t.false(row.classList.contains('payment_deferred'))
    t.true(row.classList.contains('payment_processed'))

    row = document.querySelector('tr.row3')
    t.false(row.classList.contains('payment_deferred'))
    t.false(row.classList.contains('payment_processed'))
})
