/* Phase60. Carry the original stable ID and optional owner artwork only into publicly rendered card markup.
   Original game source/rules and all existing card HTML are otherwise unchanged.
   The renderer itself hands us the card definition for visible UI. */
(() => {
  const original=window.cardHtml;
  if(typeof original!=='function')throw new Error('Original public card renderer unavailable');
  window.cardHtml=function(c,...args){
    const html=original.call(this,c,...args);
    if(!c||typeof c.id!=='string'||typeof html!=='string')return html;
    if(!window.MRRCardArtRegistry?.knownIds?.includes(c.id))return html;
    let result=html.replace('<div class="card-ui ',
      '<div data-mrr-public-card-id="'+c.id+'" class="card-ui ');
    // Original cardHtml already controls visibility. Never touch the deck or
    // facedown enemy backs. Optional owner art is restricted to this visible
    // card and remains a purely decorative <img>.
    const art=window.MRRCardArtRegistry.assets?.[c.id];
    if(typeof art==='string'&&/^data:image\/(?:png|jpeg);base64,[A-Za-z0-9+/=]+$/.test(art)){
      result=result.replace('<div class="art-well">',
        '<div class="art-well"><img class="mrr-owner-art" alt="" draggable="false" decoding="async" src="'+art+'">');
    }
    return result;
  };
})();
