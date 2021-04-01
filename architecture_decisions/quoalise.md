TODO check what happens

Consommation / production
- logique pour Cédric

Temps début / fin de période
- début, comme ça dans data connect et Viriya, semble arbitraire
- pas de pour ou contre, gardé comme implémenté

Intervalle, iso comme retourné par Enedis
- plus compact que secondes
- permet aussi de descendre sous la seconde (PT0.05s)
- nom de la balise
- spécifié pour chaque mesure? pas possible senml, surement des cas d’usages

## Use adhoc commands to expose

## Use SENML 

## Expose application specific errors

- Date: 2020-09-14
- Status: proposed
- Deciders: Cyril Lugan

### Context

Some application specific details might interest client applications to handle errors.

Ex. « This consumer has no communicating energy meter. »

For now, those errors happen when requesting  data through [XEP-0050: Ad-Hoc Commands](https://xmpp.org/extensions/xep-0050.html).

### Candidates

1. Parse and return the error in an iq :

   ```xml
   <iq xml:lang="en" to="…" type="error" id="…">
     <error type="cancel">
       <undefined-condition xmlns="urn:ietf:params:xml:ns:xmpp-stanzas" />
        <text xmlns="urn:ietf:params:xml:ns:xmpp-stanzas">The requested period cannot be anterior to the meter&apos;s last activation date</text>
        <upstream-error xmlns="urn:quoalise:0" issuer="enedis-data-connect" code="ADAM-ERR0123" />
     </error>
   </iq>
   ```

2. Return the raw error in an ad-hoc command flow :

   ```xml
   <iq xml:lang="en" to="…" type="result" id="…">
     <command xmlns="http://jabber.org/protocol/commands" node="…" sessionid="…" status="completed">
       <note type="error">{
     &quot;error&quot;: &quot;ADAM-ERR0123&quot;,
     &quot;error_description&quot;: &quot;The requested period cannot be anterior to the meter&apos;s last activation date&quot;                   
   }
    </note>
     </command>
   </iq>        
   ```

### Decision

Return the error in an iq :

- Seems more extensible
- Consistent with slixmpp handling of exception not catched by user code
- Provide a way to expose the raw upstream application error code, attributes might be added

### TODO

- Check exemples of errors handled in ad-hoc commands
- Localize error message?

## Use XMPP auth mechanisms

CONS

## Represent sensor measurements

- Date: 2019-04-23
- Id: <a name="use-senml">use-senml</a>
- Status: proposed
- Deciders: Gautier Husson, Gregory Elleouet

Use SENML to format raw data

https://tools.ietf.org/html/rfc8428

See [Rapport d’évaluation des formalismes de données](https://github.com/consometers/sen1-poc-docs/blob/master/Rapport_choix_formalisme.pdf) (fr).

## Use XMPP

- Date: 2019-03-19
- Id: <a name="use-senml">use-xmpp</a>
- Status: proposed
- Deciders: Gautier Husson, Gregory Elleouet

Use XMPP

See [Rapport d’évaluation des protocoles d’échange de données fédéré](https://github.com/consometers/sen1-poc-docs/blob/master/Rapport-choix-protocole.pdf) (fr)
