import Row from "@/components/Row";
import React from "react";

interface ChannelFormProps {
    disabled: boolean;
    required: boolean;
    value: string;
    onSubmit: (e: any) => any;
    onChange: (e: any) => any;
}

export default function ChannelForm(props: ChannelFormProps) {
    const { onSubmit, disabled } = props;
    return (
        <Row className="w-full">
            <form
                className="w-full flex justify-between items-center"
                onSubmit={onSubmit}
            >
                <input
                    type="text"
                    placeholder="Enter your NOSTR channel ID"
                    pattern="[a-f0-9]{64}"
                    title="Channel ID should be 64 lowercase hex characters"
                    className="border-2 border-[#08252E] px-2 text-black flex-grow"
                    {...props}
                />
                <button
                    type="submit"
                    className="border-2 border-[#08252E] px-8 bg-[#08252E] text-white ml-2"
                    disabled={disabled}
                >
                    {disabled ? "Loading..." : "Join"}
                </button>
            </form>
        </Row>
    );
}