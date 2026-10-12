// Rwanda's 30 districts with province and APPROXIMATE centroid (for map markers only).
module.exports = [
  ['Gasabo','Kigali City',-1.89,30.13],['Kicukiro','Kigali City',-2.00,30.10],['Nyarugenge','Kigali City',-1.96,30.05],
  ['Nyanza','Southern',-2.35,29.75],['Gisagara','Southern',-2.60,29.85],['Nyaruguru','Southern',-2.73,29.55],
  ['Huye','Southern',-2.60,29.74],['Nyamagabe','Southern',-2.47,29.40],['Ruhango','Southern',-2.22,29.78],
  ['Muhanga','Southern',-2.08,29.75],['Kamonyi','Southern',-2.00,29.90],
  ['Rulindo','Northern',-1.75,29.98],['Gakenke','Northern',-1.69,29.78],['Musanze','Northern',-1.50,29.63],
  ['Burera','Northern',-1.45,29.85],['Gicumbi','Northern',-1.58,30.07],
  ['Rwamagana','Eastern',-1.95,30.43],['Nyagatare','Eastern',-1.30,30.33],['Gatsibo','Eastern',-1.58,30.43],
  ['Kayonza','Eastern',-1.88,30.62],['Kirehe','Eastern',-2.25,30.70],['Ngoma','Eastern',-2.17,30.50],['Bugesera','Eastern',-2.23,30.15],
  ['Karongi','Western',-2.10,29.35],['Rutsiro','Western',-1.95,29.33],['Rubavu','Western',-1.68,29.35],
  ['Nyabihu','Western',-1.65,29.50],['Ngororero','Western',-1.87,29.62],['Rusizi','Western',-2.48,28.90],['Nyamasheke','Western',-2.35,29.10]
].map(([name, province, lat, lng]) => ({ name, province, lat, lng }));
