from __future__ import annotations


SOCIALS = {
    "wave": {
        "no_target": {
            "self": "You wave to anyone gathered.",
            "room": "{actor} waves to anyone gathered.",
        },
        "target": {
            "self": "You wave at {target}.",
            "target": "{actor} waves at you.",
            "room": "{actor} waves at {target}.",
        },
    },
    "nod": {
        "no_target": {
            "self": "You nod thoughtfully.",
            "room": "{actor} nods thoughtfully.",
        },
        "target": {
            "self": "You nod to {target}.",
            "target": "{actor} nods to you.",
            "room": "{actor} nods to {target}.",
        },
    },
    "smile": {
        "no_target": {
            "self": "You smile.",
            "room": "{actor} smiles.",
        },
        "target": {
            "self": "You smile at {target}.",
            "target": "{actor} smiles at you.",
            "room": "{actor} smiles at {target}.",
        },
    },
    "grin": {
        "no_target": {
            "self": "You grin.",
            "room": "{actor} grins.",
        },
        "target": {
            "self": "You grin at {target}.",
            "target": "{actor} grins at you.",
            "room": "{actor} grins at {target}.",
        },
    },
    "laugh": {
        "no_target": {
            "self": "You laugh.",
            "room": "{actor} laughs.",
        },
        "target": {
            "self": "You laugh at {target}.",
            "target": "{actor} laughs at you.",
            "room": "{actor} laughs at {target}.",
        },
    },
    "chuckle": {
        "no_target": {
            "self": "You chuckle softly.",
            "room": "{actor} chuckles softly.",
        },
        "target": {
            "self": "You chuckle at {target}.",
            "target": "{actor} chuckles at you.",
            "room": "{actor} chuckles at {target}.",
        },
    },
    "bow": {
        "no_target": {
            "self": "You bow.",
            "room": "{actor} bows.",
        },
        "target": {
            "self": "You bow to {target}.",
            "target": "{actor} bows to you.",
            "room": "{actor} bows to {target}.",
        },
    },
    "curtsy": {
        "no_target": {
            "self": "You curtsy.",
            "room": "{actor} curtsies.",
        },
        "target": {
            "self": "You curtsy to {target}.",
            "target": "{actor} curtsies to you.",
            "room": "{actor} curtsies to {target}.",
        },
    },
    "wink": {
        "no_target": {
            "self": "You wink.",
            "room": "{actor} winks.",
        },
        "target": {
            "self": "You wink at {target}.",
            "target": "{actor} winks at you.",
            "room": "{actor} winks at {target}.",
        },
    },
    "shrug": {
        "no_target": {
            "self": "You shrug.",
            "room": "{actor} shrugs.",
        },
        "target": {
            "self": "You shrug at {target}.",
            "target": "{actor} shrugs at you.",
            "room": "{actor} shrugs at {target}.",
        },
    },
    "dance": {
        "no_target": {
            "self": "You dance around.",
            "room": "{actor} dances around.",
        },
        "target": {
            "self": "You dance with {target}.",
            "target": "{actor} dances with you.",
            "room": "{actor} dances with {target}.",
        },
    },
    "clap": {
        "no_target": {
            "self": "You clap your hands.",
            "room": "{actor} claps their hands.",
        },
        "target": {
            "self": "You clap for {target}.",
            "target": "{actor} claps for you.",
            "room": "{actor} claps for {target}.",
        },
    },
    "cheer": {
        "no_target": {
            "self": "You cheer loudly!",
            "room": "{actor} cheers loudly!",
        },
        "target": {
            "self": "You cheer for {target}.",
            "target": "{actor} cheers for you.",
            "room": "{actor} cheers for {target}.",
        },
    },
    "cry": {
        "no_target": {
            "self": "You cry.",
            "room": "{actor} cries.",
        },
        "target": {
            "self": "You cry on {target}'s shoulder.",
            "target": "{actor} cries on your shoulder.",
            "room": "{actor} cries on {target}'s shoulder.",
        },
    },
    "sigh": {
        "no_target": {
            "self": "You sigh.",
            "room": "{actor} sighs.",
        },
        "target": {
            "self": "You sigh at {target}.",
            "target": "{actor} sighs at you.",
            "room": "{actor} sighs at {target}.",
        },
    },
    "yawn": {
        "no_target": {
            "self": "You yawn.",
            "room": "{actor} yawns.",
        },
        "target": {
            "self": "You yawn at {target}.",
            "target": "{actor} yawns at you.",
            "room": "{actor} yawns at {target}.",
        },
    },
    "laughhard": {
        "no_target": {
            "self": "You laugh uncontrollably.",
            "room": "{actor} laughs uncontrollably.",
        },
        "target": {
            "self": "You laugh hard at {target}.",
            "target": "{actor} laughs hard at you.",
            "room": "{actor} laughs hard at {target}.",
        },
    },
    "poke": {
        "no_target": {
            "self": "You poke the air.",
            "room": "{actor} pokes the air.",
        },
        "target": {
            "self": "You poke {target}.",
            "target": "{actor} pokes you.",
            "room": "{actor} pokes {target}.",
        },
    },
    "hug": {
        "no_target": {
            "self": "You hug yourself.",
            "room": "{actor} hugs themselves.",
        },
        "target": {
            "self": "You hug {target}.",
            "target": "{actor} hugs you.",
            "room": "{actor} hugs {target}.",
        },
    },
    "kiss": {
        "no_target": {
            "self": "You blow a kiss.",
            "room": "{actor} blows a kiss.",
        },
        "target": {
            "self": "You kiss {target}.",
            "target": "{actor} kisses you.",
            "room": "{actor} kisses {target}.",
        },
    },
    "slap": {
        "no_target": {
            "self": "You slap the air.",
            "room": "{actor} slaps the air.",
        },
        "target": {
            "self": "You slap {target}.",
            "target": "{actor} slaps you.",
            "room": "{actor} slaps {target}.",
        },
    },
    "glare": {
        "no_target": {
            "self": "You glare.",
            "room": "{actor} glares.",
        },
        "target": {
            "self": "You glare at {target}.",
            "target": "{actor} glares at you.",
            "room": "{actor} glares at {target}.",
        },
    },
    "stare": {
        "no_target": {
            "self": "You stare into space.",
            "room": "{actor} stares into space.",
        },
        "target": {
            "self": "You stare at {target}.",
            "target": "{actor} stares at you.",
            "room": "{actor} stares at {target}.",
        },
    },
    "wavehappy": {
        "no_target": {
            "self": "You wave happily.",
            "room": "{actor} waves happily.",
        },
        "target": {
            "self": "You wave happily at {target}.",
            "target": "{actor} waves happily at you.",
            "room": "{actor} waves happily at {target}.",
        },
    },
}
