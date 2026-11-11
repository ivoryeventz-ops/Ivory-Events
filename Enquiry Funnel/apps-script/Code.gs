/**
 * Shared storage for the Enquiry Funnel's "Outside vendors" ticks and notes.
 *
 * Setup (once):
 * 1. Create a new Google Sheet, name it "Ivory Vendor Bookings".
 * 2. In the sheet: Extensions > Apps Script. Delete the sample code and paste this file.
 * 3. Change SECRET below to a private word.
 * 4. Deploy > New deployment > type "Web app" > Execute as: Me > Who has access: Anyone > Deploy.
 *    Allow the permissions it asks for. Copy the Web app URL (ends in /exec).
 * 5. In the Enquiry Funnel, open any confirmed work, open "Shared saving", paste the URL and the
 *    secret word, and press "Save on this device". Repeat once on Anila's phone/computer.
 *
 * Each vendor tick/note becomes one row in the "Vendors" tab, so it is also easy to read in the sheet.
 * If you change this code later: Deploy > Manage deployments > edit > New version.
 */
const SECRET = 'CHANGE-THIS-WORD';
const TAB = 'Vendors';
const HEAD = ['WorkKey', 'Vendor', 'Details', 'Booked', 'UpdatedAt'];

function tab_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(TAB);
  if (!sh) {
    sh = ss.insertSheet(TAB);
    sh.appendRow(HEAD);
    sh.setFrozenRows(1);
    sh.getRange('A:C').setNumberFormat('@'); // keep text as typed (no phone numbers or "=" turning into formulas)
  }
  return sh;
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.key !== SECRET) return out_({ ok: false, error: 'Wrong secret word' });
  const v = tab_().getDataRange().getValues().slice(1);
  const rows = v.filter(r => r[0]).map(r => ({
    workKey: String(r[0]),
    vendor: String(r[1]),
    details: String(r[2] || ''),
    booked: r[3] === true || String(r[3]).toLowerCase() === 'true'
  }));
  return out_({ ok: true, rows: rows });
}

function doPost(e) {
  let b;
  try { b = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'Bad request' }); }
  if (b.key !== SECRET) return out_({ ok: false, error: 'Wrong secret word' });
  if (b.action !== 'save' || !b.workKey || !b.vendor) return out_({ ok: false, error: 'Bad request' });

  const lock = LockService.getScriptLock();
  lock.waitLock(15000); // two people saving at the same moment wait their turn
  try {
    const sh = tab_();
    const data = sh.getDataRange().getValues();
    let row = -1;
    for (let i = 1; i < data.length; i++) {
      if (String(data[i][0]) === b.workKey && String(data[i][1]) === b.vendor) { row = i + 1; break; }
    }
    if (row < 0) {
      sh.appendRow([b.workKey, b.vendor, '', false, new Date()]);
      row = sh.getLastRow();
    }
    const f = b.fields || {};
    // Only the fields that changed are written, so a tick by one person never wipes a note typed by the other.
    if ('details' in f) sh.getRange(row, 3).setNumberFormat('@').setValue(String(f.details));
    if ('booked' in f) sh.getRange(row, 4).setValue(f.booked === true);
    sh.getRange(row, 5).setValue(new Date());
    return out_({ ok: true });
  } finally {
    lock.releaseLock();
  }
}
