/* Phase59. Add only the original stable ID to already-public card markup.
   Original game source/rules and all existing card HTML are otherwise unchanged.
   The renderer itself hands us the card definition for visible UI. */
(() => {
  const original=window.cardHtml;
  if(typeof original!=='function')throw new Error('Original public card renderer unavailable');
  window.cardHtml=function(c,...args){
    const html=original.call(this,c,...args);
    if(!c||typeof c.id!=='string'||typeof html!=='string')return html;
    if(!window.MRRCardArtRegistry?.knownIds?.includes(c.id))return html;
    return html.replace('<div class="card-ui ',
      '<div data-mrr-public-card-id="'+c.id+'" class="card-ui ');
  };
})();
