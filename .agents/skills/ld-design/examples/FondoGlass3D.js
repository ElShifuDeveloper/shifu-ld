// Fondo 3D OPCIONAL para el tema Soft Glass (Three.js). No forma parte del kit base ni se carga por defecto.
// Solo se usa si la persona lo pide. Three.js es una librería EXTERNA de diseño: va como archivo LOCAL
// (Static/vendor/three.module.min.js, versión fijada), nunca desde una CDN; el funcionamiento de la pantalla no depende de ella.
//
// Uso (módulo ES, al final del <body>):
//   <script type="module">
//     import * as THREE from "{% static 'vendor/three.module.min.js' %}";
//     import { FondoGlass3D } from "{% static 'scripts/FondoGlass3D.js' %}";
//     FondoGlass3D(THREE);
//   </script>
//
// Dibuja esferas translúcidas suaves que flotan detrás de las tarjetas de vidrio (el desenfoque de LD.css las difumina).
// Respeta prefers-reduced-motion (un solo cuadro, sin animación), se pausa con la pestaña oculta, limita la densidad de píxeles
// y, si WebGL no está disponible o falla, no hace nada: queda el degradado CSS. Devuelve una función para destruirlo.

export function FondoGlass3D(THREE, opciones) {
	var op = Object.assign({ esferas: 7, velocidad: 0.25 }, opciones || {});
	var lienzo = document.createElement("canvas");
	lienzo.className = "ld-fondo3d";
	lienzo.setAttribute("aria-hidden", "true");
	var renderer;
	try {
		renderer = new THREE.WebGLRenderer({ canvas: lienzo, alpha: true, antialias: true, powerPreference: "low-power" });
	} catch (e) {
		return function () { };   // sin WebGL: se queda el fondo CSS
	}
	document.body.prepend(lienzo);
	renderer.setClearColor(0x000000, 0);
	renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

	var escena = new THREE.Scene();
	var camara = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
	camara.position.z = 12;
	escena.add(new THREE.AmbientLight(0xffffff, 1.6));
	var luz = new THREE.DirectionalLight(0xffffff, 2.2);
	luz.position.set(4, 6, 8);
	escena.add(luz);

	// Colores desde los tokens de LD.css (así siguen la marca y el tema claro u oscuro)
	var estilo = getComputedStyle(document.documentElement);
	var paleta = [estilo.getPropertyValue("--ld-primario"), "#b9a8ff", "#9fd3ff", "#ffc9e0"]
		.map(function (c) { return new THREE.Color(c.trim() || "#8aa0ff"); });

	var esferas = [];
	for (var i = 0; i < op.esferas; i++) {
		var radio = 0.9 + (i % 3) * 0.55;
		var malla = new THREE.Mesh(
			new THREE.SphereGeometry(radio, 48, 48),
			new THREE.MeshStandardMaterial({ color: paleta[i % paleta.length], transparent: true, opacity: 0.38, roughness: 0.25, metalness: 0.1 })
		);
		malla.position.set((i / op.esferas) * 22 - 11, ((i * 37) % 11) - 5.5, -2 - (i % 4));
		malla.userData = { fase: i * 1.7, amplitud: 0.35 + (i % 3) * 0.2, base: malla.position.clone() };
		escena.add(malla);
		esferas.push(malla);
	}

	function ajustar() {
		var ancho = window.innerWidth, alto = window.innerHeight;
		renderer.setSize(ancho, alto, false);
		camara.aspect = ancho / alto;
		camara.updateProjectionMatrix();
	}
	function dibujar(t) {
		esferas.forEach(function (m) {
			var d = m.userData;
			m.position.y = d.base.y + Math.sin(t * op.velocidad + d.fase) * d.amplitud;
			m.position.x = d.base.x + Math.cos(t * op.velocidad * 0.7 + d.fase) * d.amplitud * 0.6;
		});
		renderer.render(escena, camara);
	}

	var reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
	var marco = 0;
	function ciclo(ms) {
		dibujar(ms / 1000);
		marco = requestAnimationFrame(ciclo);
	}
	function visibilidad() {
		cancelAnimationFrame(marco);
		if (!document.hidden && !reducido) marco = requestAnimationFrame(ciclo);
	}
	ajustar();
	window.addEventListener("resize", ajustar);
	document.addEventListener("visibilitychange", visibilidad);
	dibujar(0);
	visibilidad();

	return function destruir() {
		cancelAnimationFrame(marco);
		window.removeEventListener("resize", ajustar);
		document.removeEventListener("visibilitychange", visibilidad);
		esferas.forEach(function (m) { m.geometry.dispose(); m.material.dispose(); });
		renderer.dispose();
		lienzo.remove();
	};
}
