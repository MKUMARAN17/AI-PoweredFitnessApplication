/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#0EA5E9",
                secondary: "#22D3EE",
                accent: "#38BDF8",
                background: "#0D1117",
                surface: "#161B22",
                "surface-hover": "#1F2937",
                text: "#F0F6FC",
                "text-muted": "#8B949E",
            },
            fontFamily: {
                heading: ['Outfit', 'sans-serif'],
                body: ['Plus Jakarta Sans', 'sans-serif'],
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
            }
        },
    },
    plugins: [],
}
