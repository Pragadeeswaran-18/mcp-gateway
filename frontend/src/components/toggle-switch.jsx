import React from "react";

export function ToggleSwitch({ id, checked, onChange, label }) {
    const styles = {
        wrapper: {
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            userSelect: "none",
        },
        checkbox: {
            height: 0,
            width: 0,
            visibility: "hidden",
            position: "absolute",
        },
        label: {
            cursor: "pointer",
            width: "44px",
            height: "24px",
            background: checked ? "#0d6efd" : "#ccc", // blue if checked, gray otherwise
            borderRadius: "20px",
            position: "relative",
            transition: "background-color 0.3s ease",
            display: "inline-block",
        },
        button: {
            content: '""',
            position: "absolute",
            top: "2px",
            left: checked ? "22px" : "2px",
            width: "20px",
            height: "20px",
            background: "white",
            borderRadius: "50%",
            transition: "left 0.3s",
            boxShadow: "0 0 2px rgba(0,0,0,0.2)",
        },
        text: {
            fontSize: "0.9rem",
            color: "#212529",
        },
    };

    return (
        <div style={styles.wrapper}>
            <span style={styles.text}>{label}</span> {/* Label moved here */}
            <label htmlFor={id} style={styles.label}>
                <span style={styles.button} />
            </label>
            <input
                type="checkbox"
                id={id}
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
                style={styles.checkbox}
            />
        </div>
    );
}
