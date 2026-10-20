-- Las bases neutralizadas (staging de Odoo.sh) son copias de produccion:
-- no deben llevar las contrasenas reales.
UPDATE dako_password
   SET password = 'neutralizada',
       strength = 'weak',
       strength_score = 0;
