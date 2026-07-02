export default function ErrorPanel({
    error
}) {

    if (!error) {
        return null;
    }

    return (

        <div
            style={{
                background: "#fff2f0",
                color: "#a8071a",
                padding: 20,
                borderRadius: 8
            }}
        >
            {error}
        </div>

    );
}