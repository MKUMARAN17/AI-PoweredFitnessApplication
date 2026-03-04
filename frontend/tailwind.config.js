/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#8B5CF6",
                secondary: "#EC4899",
                accent: "#10B981",
                background: "#0F172A",
                surface: "#1E293B",
                "surface-hover": "#334155",
                text: "#F8FAFC",
                "text-muted": "#94A3B8",
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
