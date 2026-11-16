// Copies of the plain game's rows for the templates a skill-page mod builds its rows from.
// Canonical copy: StockRows.py pastes this block into each skill-page mod's mod.js (D2RMM mods
// cannot share code), together with that mod's STOCK_ROWS table.
//
// A page mod copies stock rows (a skill, its description, missiles, states, monsters, items) and
// fills in its own columns; every column it leaves alone keeps the copied value. A mod installed
// before it that reworks those stock rows (a total conversion) would leak its edits into the new
// rows, so the copies come from the plain game's rows. StockRows.py finds the names by running
// the mod on the plain game (ModHarness.js) and embeds those rows in STOCK_ROWS.
//
//   stockSet               rule set being patched: 'main' (global\excel) or 'base'
//                          (global\excel\base); the mod sets it for each set of tables
//   stockRow(tsv, col, name, file, set)
//     tsv                  the table being patched; the copy has its columns
//     col, name            key column and the row's name (any case)
//     file                 table file without .txt, when the key column does not tell
//                          (STOCK_KEY_FILES: 'Id' is monstats, so monsounds passes 'monsounds')
//     set                  rule set to take the row from (default stockSet)
//   returns                a new copy of the plain game's row; null when the plain game's table
//                          has no such row; undefined when STOCK_ROWS does not have the name
//                          (the caller then copies the row as it is now)
let stockSet = 'main';
const STOCK_KEY_FILES = {
  skill: 'skills', skilldesc: 'skilldesc', Missile: 'missiles', state: 'states', 'pet type': 'pettype',
  Id: 'monstats', Sound: 'sounds', Code: 'itemtypes', code: 'weapons',
};
const stockIndex = {};
function stockRow(tsv, col, name, file, set) {
  const table = file || STOCK_KEY_FILES[col];
  const which = set || stockSet;
  const key = String(name).toLowerCase();
  // StockRows.py runs the mod with this option on to learn which rows it copies.
  if (typeof config !== 'undefined' && config && config.recordStockRows) console.log(`[stock-rows] ${table}\t${col}\t${name}`);
  if (!table) return undefined;
  const lookup = (rows, id) => {
    if (!rows) return undefined;
    if (!stockIndex[id]) {
      stockIndex[id] = {};
      Object.keys(rows).forEach((k) => {
        stockIndex[id][k.toLowerCase()] = rows[k];
      });
    }
    return stockIndex[id][key];
  };
  let row = which === 'base' ? lookup(STOCK_ROWS_BASE[table], `base/${table}`) : undefined;
  if (row === undefined) row = lookup(STOCK_ROWS[table], table);
  if (row === undefined || row === null) return row;
  const copy = {};
  tsv.headers.forEach((h) => {
    copy[h] = row[h] === undefined ? '' : row[h];
  });
  return copy;
}
